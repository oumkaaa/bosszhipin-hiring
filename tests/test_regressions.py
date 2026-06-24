import asyncio
import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))


class DummyLogger:
    def __getattr__(self, name):
        def log(*args, **kwargs):
            return None
        return log


def test_auth_status_parses_boss_json_envelope():
    from boss_hr_recruiter.adapters.agentcli import AgentCliAdapter

    completed = SimpleNamespace(
        returncode=0,
        stdout=json.dumps({
            "ok": True,
            "data": {"auth_summary": "ok", "auth_state": "full"},
            "error": None,
        }),
        stderr="",
    )

    with patch("boss_hr_recruiter.adapters.agentcli.BossRecruiterClient"):
        with patch("subprocess.run", return_value=completed) as run:
            adapter = AgentCliAdapter(auth=object(), logger=DummyLogger())
            result = adapter.check_auth_status()

    assert result["code"] == 0
    assert result["ok"] is True
    assert result["data"]["auth_summary"] == "ok"
    assert run.call_args.args[0] == ["boss", "--json", "status", "--live"]
    assert run.call_args.kwargs["encoding"].lower().replace("-", "") == "utf8"


def test_phase1_dry_run_keeps_adapter_open_and_merges_by_friend_id():
    main_mod = importlib.import_module("boss_hr_recruiter.main")
    sources_mod = importlib.import_module("boss_hr_recruiter.phase1.sources")
    allocator_mod = importlib.import_module("boss_hr_recruiter.phase1.allocator")

    saved = {}

    class FakeClient:
        def __init__(self, auth):
            return None

        def close(self):
            return None

    class FakeStorage:
        def load(self):
            return [{"friendId": 123, "name": "Old", "status": "NEW"}]

        def save(self, candidates):
            saved["candidates"] = candidates

    class FakeAdapter:
        def __init__(self, auth, logger):
            self.closed = False

        def send_message(self, friend_id, content, dry_run=False):
            assert self.closed is False
            assert friend_id == 123
            assert content == "hello"
            assert dry_run is True
            return {"code": 0, "message": "dry_run", "dry_run": True}

        def close(self):
            self.closed = True

    async def fake_fetch_all_candidates(client, job_id, max_recommend_pages, logger_obj):
        return {"chat": [{"friendId": 123, "name": "Alice", "source": "chat"}], "recommend": []}

    def fake_screen_and_rate(**kwargs):
        return {"name": "Alice", "source": "chat", "screen_result": "PASS", "score": 88.0, "resume_data": {}}

    with patch.object(main_mod, "BossRecruiterClient", FakeClient):
        with patch.object(main_mod, "screen_and_rate", fake_screen_and_rate):
            with patch.object(main_mod, "AgentCliAdapter", FakeAdapter, create=True):
                with patch.object(sources_mod, "fetch_all_candidates", fake_fetch_all_candidates):
                    with patch.object(sources_mod, "deduplicate_candidates", lambda chat, rec, logger_obj=None: chat + rec):
                        with patch.object(allocator_mod, "allocate_candidates_by_quota", lambda candidates, target_count, source_ratio=None, logger_obj=None: candidates):
                            asyncio.run(main_mod.run_phase1(
                                logger=DummyLogger(),
                                auth=object(),
                                config={
                                    "task_status": "active",
                                    "job_id": "job",
                                    "greet_batch_size": 1,
                                    "first_round_message": "hello",
                                    "dry_run": True,
                                    "screen_rules": {},
                                },
                                storage=FakeStorage(),
                            ))

    assert len(saved["candidates"]) == 1
    assert saved["candidates"][0]["name"] == "Alice"
    assert saved["candidates"][0]["status"] == "首轮沟通"


def test_phase2_dry_run_records_follow_up_send():
    main_mod = importlib.import_module("boss_hr_recruiter.main")

    saved = {}

    class FakeStorage:
        def load(self):
            return [{"friendId": 123, "name": "Alice", "status": "首轮沟通"}]

        def save(self, candidates):
            saved["candidates"] = candidates

    class FakeAdapter:
        def __init__(self, auth, logger):
            return None

        def get_latest_messages(self, friend_ids):
            assert friend_ids == [123]
            return {"code": 0, "zpData": {"messages": [{"content": "可以，尽快到岗"}]}}

        def send_message(self, friend_id, content, dry_run=False):
            assert friend_id == 123
            assert content == "please clarify"
            assert dry_run is True
            return {"code": 0, "message": "dry_run", "dry_run": True}

        def close(self):
            return None

    with patch.object(main_mod, "AgentCliAdapter", FakeAdapter, create=True):
        asyncio.run(main_mod.run_phase2(
            logger=DummyLogger(),
            auth=object(),
            config={
                "task_status": "active",
                "dry_run": True,
                "follow_up_message": "please clarify",
                "screen_rules": {"max_arrival_weeks": 2, "min_days_per_week": 4, "min_duration_months": 3},
            },
            storage=FakeStorage(),
        ))

    assert saved["candidates"][0]["status"] == "首轮沟通追加提问"
    assert saved["candidates"][0]["last_agentcli_result"] == {
        "code": 0,
        "action": "send_message",
        "message_type": "follow_up",
    }


def test_adapter_normalizes_last_message_list_and_passes_security_id():
    from boss_hr_recruiter.adapters.agentcli import AgentCliAdapter

    class FakeClient:
        def __init__(self, auth):
            self.view_args = None

        def last_messages(self, friend_ids):
            return {"code": 0, "zpData": {"lastMessageList": [{"friendId": 123, "last_msg": "hello"}]}}

        def view_geek(self, geek_id, job_id, security_id=None):
            self.view_args = (geek_id, job_id, security_id)
            return {"code": 0, "zpData": {}}

        def close(self):
            return None

    with patch("boss_hr_recruiter.adapters.agentcli.BossRecruiterClient", FakeClient):
        adapter = AgentCliAdapter(auth=object(), logger=DummyLogger())
        messages = adapter.get_latest_messages([123])
        adapter.get_resume("geek", "job", "sec")

    assert messages["zpData"]["messages"][0]["content"] == "hello"
    assert adapter.client.view_args == ("geek", "job", "sec")


def test_screening_passes_security_id_to_view_geek():
    from boss_hr_recruiter.phase1.screening import screen_and_rate

    class FakeClient:
        def __init__(self):
            self.view_args = None

        def friend_detail(self, friend_ids):
            return {
                "code": 0,
                "zpData": {
                    "friendList": [{"encryptUid": "geek", "encryptJobId": "job", "securityId": "sec"}],
                },
            }

        def view_geek(self, geek_id, job_id, security_id=None):
            self.view_args = (geek_id, job_id, security_id)
            return {
                "code": 0,
                "data": {
                    "zpData": {
                        "geekDetailInfo": {
                            "geekBaseInfo": {"degreeCategory": "本科", "workYearDesc": "28年应届生"},
                            "geekWorkExpList": [],
                            "geekEduExpList": [{"schoolName": "Test University", "majorName": "AI产品", "tags": []}],
                        },
                    },
                },
            }

    client = FakeClient()
    result = screen_and_rate(
        candidate={"friendId": 123, "name": "Alice", "source": "chat"},
        client=client,
        config={},
        rules={"valid_degrees": ["本科"], "min_grad_year": 2026},
        logger=DummyLogger(),
    )

    assert result["screen_result"] == "PASS"
    assert client.view_args == ("geek", "job", "sec")


def test_chat_list_candidates_accept_zpdata_result_and_preserve_identifiers():
    from boss_hr_recruiter.phase1.sources import fetch_chat_list_candidates

    class FakeClient:
        def friend_list(self, page, label_id, job_id):
            return {
                "code": 0,
                "zpData": {
                    "result": [
                        {
                            "uid": 123,
                            "name": "Alice",
                            "encryptFriendId": "friend-enc",
                            "encryptUid": "uid-enc",
                            "encryptGeekId": "geek-enc",
                            "encryptJobId": "job-enc",
                            "securityId": "sec-id",
                        },
                    ],
                },
            }

    candidates = asyncio.run(fetch_chat_list_candidates(FakeClient(), "job"))

    assert len(candidates) == 1
    assert candidates[0]["friendId"] == 123
    assert candidates[0]["name"] == "Alice"
    assert candidates[0]["source"] == "chat"
    assert candidates[0]["encryptFriendId"] == "friend-enc"
    assert candidates[0]["encryptUid"] == "uid-enc"
    assert candidates[0]["encryptGeekId"] == "geek-enc"
    assert candidates[0]["encryptJobId"] == "job-enc"
    assert candidates[0]["securityId"] == "sec-id"


def test_screening_uses_candidate_identifiers_before_friend_detail():
    from boss_hr_recruiter.phase1.screening import screen_and_rate

    class FakeClient:
        def __init__(self):
            self.friend_detail_called = False
            self.view_args = None

        def friend_detail(self, friend_ids):
            self.friend_detail_called = True
            raise AssertionError("friend_detail should not be called when candidate identifiers are present")

        def view_geek(self, geek_id, job_id, security_id=None):
            self.view_args = (geek_id, job_id, security_id)
            return {
                "code": 0,
                "data": {
                    "zpData": {
                        "geekDetailInfo": {
                            "geekBaseInfo": {"degreeCategory": "本科", "workYearDesc": "28年应届生"},
                            "geekWorkExpList": [],
                            "geekEduExpList": [{"schoolName": "Test University", "majorName": "AI产品", "tags": []}],
                        },
                    },
                },
            }

    client = FakeClient()
    result = screen_and_rate(
        candidate={
            "friendId": 123,
            "name": "Alice",
            "source": "chat",
            "encryptGeekId": "geek-from-list",
            "encryptJobId": "job-from-list",
            "encryptFriendId": "friend-enc-not-security",
            "securityId": "sec-from-list",
        },
        client=client,
        config={},
        rules={"valid_degrees": ["本科"], "min_grad_year": 2026},
        logger=DummyLogger(),
    )

    assert result["screen_result"] == "PASS"
    assert client.friend_detail_called is False
    assert client.view_args == ("geek-from-list", "job-from-list", "sec-from-list")


def test_screening_does_not_treat_encrypt_friend_id_as_security_id():
    from boss_hr_recruiter.phase1.screening import screen_and_rate

    class FakeClient:
        def __init__(self):
            self.view_args = None

        def friend_detail(self, friend_ids):
            return {
                "code": 0,
                "zpData": {
                    "friendList": [{"encryptUid": "geek", "encryptJobId": "job"}],
                },
            }

        def view_geek(self, geek_id, job_id, security_id=None):
            self.view_args = (geek_id, job_id, security_id)
            return {
                "code": 0,
                "data": {
                    "zpData": {
                        "geekDetailInfo": {
                            "geekBaseInfo": {"degreeCategory": "本科", "workYearDesc": "28年应届生"},
                            "geekWorkExpList": [],
                            "geekEduExpList": [{"schoolName": "Test University", "majorName": "AI产品", "tags": []}],
                        },
                    },
                },
            }

    client = FakeClient()
    result = screen_and_rate(
        candidate={
            "friendId": 123,
            "name": "Alice",
            "source": "chat",
            "encryptFriendId": "friend-enc-not-security",
        },
        client=client,
        config={},
        rules={"valid_degrees": ["本科"], "min_grad_year": 2026},
        logger=DummyLogger(),
    )

    assert result["screen_result"] == "PASS"
    assert client.view_args == ("geek", "job", None)


def test_phase3_dry_run_does_not_update_task_status():
    main_mod = importlib.import_module("boss_hr_recruiter.main")
    called = {"update": False}

    class FakeStorage:
        def load(self):
            return []

        def save(self, candidates):
            return None

    class FakeAdapter:
        def __init__(self, auth, logger):
            return None

        def close(self):
            return None

    def fake_judge_goal_completion(runtime_dir):
        return {
            "is_completed": False,
            "is_expired": True,
            "resume_count": 0,
            "resume_target": 1,
            "task_status": "expired",
            "reason": "Deadline passed",
        }

    def fake_update_task_status(*args, **kwargs):
        called["update"] = True

    with patch.object(main_mod, "AgentCliAdapter", FakeAdapter, create=True):
        with patch.object(main_mod, "judge_goal_completion", fake_judge_goal_completion):
            with patch.object(main_mod, "update_task_status", fake_update_task_status):
                asyncio.run(main_mod.run_phase3(
                    logger=DummyLogger(),
                    auth=object(),
                    config={"runtime_dir": "runtime", "dry_run": True, "resume_target": 1},
                    storage=FakeStorage(),
                ))

    assert called["update"] is False


if __name__ == "__main__":
    tests = [
        test_auth_status_parses_boss_json_envelope,
        test_phase1_dry_run_keeps_adapter_open_and_merges_by_friend_id,
        test_phase2_dry_run_records_follow_up_send,
        test_adapter_normalizes_last_message_list_and_passes_security_id,
        test_screening_passes_security_id_to_view_geek,
        test_chat_list_candidates_accept_zpdata_result_and_preserve_identifiers,
        test_screening_uses_candidate_identifiers_before_friend_detail,
        test_screening_does_not_treat_encrypt_friend_id_as_security_id,
        test_phase3_dry_run_does_not_update_task_status,
    ]
    failures = 0
    for test in tests:
        try:
            test()
            print(f"PASS {test.__name__}")
        except Exception as exc:
            failures += 1
            print(f"FAIL {test.__name__}: {type(exc).__name__}: {exc}")
    raise SystemExit(1 if failures else 0)
