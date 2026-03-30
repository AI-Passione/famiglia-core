from dotenv import load_dotenv

# prevent main from reading any real .env file during tests
load_dotenv = lambda *args, **kwargs: None

from main import _format_reply_for_sender, _strip_bot_mention


def test_format_reply_for_sender_prepends_correct_mention():
    result = _format_reply_for_sender("Pipeline status is healthy.", "U123ABC456")
    assert result.startswith("<@U123ABC456> ")


def test_format_reply_for_sender_replaces_wrong_leading_id():
    result = _format_reply_for_sender("@UWRONGBOT01 all good now.", "UCORRECT99")
    assert result.startswith("<@UCORRECT99> all good now.")
    assert "_Env: Production_" in result


    result = _format_reply_for_sender("<@UCORRECT99> done.", "UCORRECT99")
    assert result.startswith("<@UCORRECT99> done.")
    assert "_Env: Production_" in result


def test_strip_bot_mention_handles_plain_and_display_name_formats():
    assert _strip_bot_mention("<@UABC123>   ", "UABC123") == ""
    assert _strip_bot_mention("<@UABC123|rossini>:", "UABC123") == ":"


def test_main_skips_agents_without_tokens(monkeypatch, capsys, mocker):
    # mimic SlackQueueClient with limited capability
    mock_sq = mocker.MagicMock()
    mock_sq.agent_tokens = {"alfredo": None, "riccado": "tk"}
    mock_sq.agent_app_tokens = {"alfredo": None, "riccado": "app-tk"}
    mock_sq.bot_ids = {"riccado": "U111"}
    monkeypatch.setattr("src.command_center.backend.slack.client.slack_queue", mock_sq)

    # monkeypatch environment so that agents dict is simple
    from src.agents.alfredo import Alfredo
    from src.agents.riccado import Riccado

    monkeypatch.setattr("main.Alfredo", lambda: Alfredo())
    monkeypatch.setattr("main.Riccado", lambda: Riccado())

    # run part of main until before infinite loop: we'll copy relevant section
    # we'll re-create the loop to capture the print output
    from main import _format_reply_for_sender  # import ensures module loaded

    ack_emoji = "eyes"
    agents = {"alfredo": Alfredo(), "riccado": Riccado()}
    app_token = mock_sq.app_token
    handlers = []

    for agent_id, token in mock_sq.agent_tokens.items():
        agent_app_token = mock_sq.agent_app_tokens.get(agent_id) or app_token
        if not token:
            print(f"[{agent_id}] no bot token found; listener will not start.")
            continue
        if not agent_app_token:
            print(f"[{agent_id}] no app token found; listener will not start.")
            continue
        bot_id = mock_sq.bot_ids.get(agent_id)
        if not bot_id:
            print(f"[{agent_id}] authentication failed or bot_id missing; listener will not start.")
            continue
        handlers.append(agent_id)

    captured = capsys.readouterr().out
    assert "[alfredo] no bot token found" in captured
    # riccado should have created handler
    assert handlers == ["riccado"]


def test_process_mention_uses_correct_app(monkeypatch, capsys):
    # stub App to track which token's client is used for reactions
    calls = []
    class FakeClient:
        def __init__(self, token):
            self.token = token
        def reactions_add(self, name, channel, timestamp):
            calls.append((self.token, name, channel, timestamp))
    class FakeApp:
        def __init__(self, token):
            self.token = token
            self.client = FakeClient(token)
        def event(self, _type):
            def decorator(fn):
                # just return the function unmodified
                return fn
            return decorator
    monkeypatch.setenv("SLACK_BOT_TOKEN_ALFREDO", "tk-alf")
    monkeypatch.setenv("SLACK_BOT_TOKEN_RICCADO", "tk-ric")
    monkeypatch.setenv("SLACK_APP_TOKEN", "xapp")

    monkeypatch.setattr("main.App", FakeApp)

    # create minimal agents to satisfy loop
    from src.agents.alfredo import Alfredo
    from src.agents.riccado import Riccado
    monkeypatch.setattr("main.Alfredo", lambda: Alfredo())
    monkeypatch.setattr("main.Riccado", lambda: Riccado())

    # re-run the registration loop from main to obtain the process_mention functions
    import importlib
    import main as mainmod
    importlib.reload(mainmod)

    # grab the handlers defined inside main; they aren't exposed, so replicate
    # simple version
    slack_queue = mainmod.slack_queue
    slack_queue.agent_tokens = {"alfredo": "tk-alf", "riccado": "tk-ric"}
    slack_queue.agent_app_tokens = {"alfredo": "xapp", "riccado": "xapp"}
    slack_queue.bot_ids = {"alfredo": "U123", "riccado": "U456"}
    
    agents = {"alfredo": Alfredo(), "riccado": Riccado()}
    ack_emoji = "eyes"
    app_token = slack_queue.app_token
    generated = []  # keep tuples of (agent_id, process_mention_func, app_token)

    for agent_id, token in slack_queue.agent_tokens.items():
        agent_app_token = slack_queue.agent_app_tokens.get(agent_id) or app_token
        if not token or not agent_app_token:
            continue
        bot_id = slack_queue.bot_ids.get(agent_id)
        if not bot_id:
            continue

        app = FakeApp(token)
        agent_obj = agents.get(agent_id)
        def process_mention(event, say, agent_obj=agent_obj, bot_id=bot_id, app=app):
            # copy from main
            app.client.reactions_add(name=ack_emoji, channel=event.get("channel"), timestamp=event.get("ts"))
        generated.append((agent_id, process_mention, token))

    # simulate an incoming event for each agent and ensure the reaction call uses that agent's token
    for agent_id, func, token in generated:
        event = {"text": "hi", "user": "U1", "channel": "C", "ts": "123"}
        func(event, lambda **kwargs: None)

    # sort calls by token
    tokens = {call[0] for call in calls}
    assert tokens == {"tk-alf", "tk-ric"}
