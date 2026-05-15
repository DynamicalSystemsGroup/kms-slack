from app.config import VERSION, DEFAULT_DM_MODE
from os import environ
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from slack_bolt.async_app import AsyncApp
import asyncio
from app.interaction_handlers import conversational, direct, agentic
import os
from app.message import Message
from dotenv import load_dotenv

load_dotenv()

dm_mode = "conversational"
app = AsyncApp(token=os.getenv("SLACK_APP_TOKEN"))


@app.command("/chat")
async def command_chat(ack, body, logger):
    await ack()
    prompt = body["text"]
    channel = body["channel_id"]
    user = body["user_id"]
    content = f"<@{user}> prompted:\n{prompt}"
    initial_message = Message(
        content, channel, thread_ts=None, display_name="KMS - Chat"
    )
    await conversational(
        prompt, user, channel, initial_message.message_ts, thread_ts=None
    )


@app.command("/agent")
async def command_agent(ack, body, logger):
    await ack()
    prompt = body["text"]
    channel = body["channel_id"]
    user = body["user_id"]
    content = f"<@{user}> prompted:\n{prompt}"
    initial_message = Message(
        content, channel, thread_ts=None, display_name="KMS - Agent"
    )
    await agentic(prompt, user, channel, initial_message.message_ts, thread_ts=None)


@app.event("app_mention")
async def handle_mention(body):
    """Handles a message event from slack. Called when a user mentions the bot in a channel."""
    prompt = (
        str(body["event"]["text"]).split(f"<@{os.getenv('SLACK_BOT_USER_ID')}>")[1].strip()
    )
    prompt = body["event"]["text"]
    channel = body["event"]["channel"]
    ts = body["event"]["ts"]
    thread_ts = body["event"].get("thread_ts")
    user = body["event"]["user"]
    await conversational(prompt, user, channel, ts, thread_ts)


@app.event("message")
async def messaged(event):
    # make sure we actually want to respond to this message
    if event["channel_type"] != "im":
        return
    if "bot_id" in event or "bot_id" in event.get("message", ()):
        return
    if "subtype" in event and event["subtype"] == "message_changed":
        return

    # setup query and response
    prompt = event["text"]
    channel = event["channel"]
    thread_ts = event.get("thread_ts")
    ts = event["ts"]
    user = event["user"]

    if dm_mode == "direct":
        await direct(prompt, user, channel, ts, thread_ts)
    elif dm_mode == "conversational":
        await conversational(prompt, user, channel, ts, thread_ts)
    elif dm_mode == "agentic" or dm_mode is None:
        await agentic(prompt, user, channel, ts, thread_ts)


@app.action("dm_mode_select")
async def update_mode(ack, body):
    # new_mode = body["actions"][0]["selected_option"]["value"]
    # user = body["user"]["id"]
    # prefs.set_dm_mode(user, new_mode)
    await ack()


@app.event("app_home_opened")
async def update_home_tab(client, event, logger):
    # user = event["user"]
    current_mode = dm_mode
    print("current dm mode:", current_mode)

    if current_mode is None:
        # prefs.set_dm_mode(user, DEFAULT_DM_MODE)
        current_mode = DEFAULT_DM_MODE

    try:
        await client.views_publish(
            token=environ["SLACK_BOT_TOKEN"],
            user_id=event["user"],
            view={
                "type": "home",
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"Hi <@{event['user']}>! :wave:",
                        },
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "I am a slack bot interface for KMS. These are a few things which you can do:",
                        },
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "• Ask <@U055TK4J9NG> + GPT questions in direct messages\n • Have conversations with <@U055TK4J9NG> + GPT in public channels\n• Search and query the knowledgebase \n ",
                        },
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "Launch KMS in browser",
                                },
                                "url": "https://kms.dynamicalsystemsgroup.com",
                            }
                        ],
                    },
                    {"type": "divider"},
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": "Interaction Mode",
                            "emoji": True,
                        },
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*Conversational:* Starts a thread and remembers messages like chatGPT.\n*Direct:* Responds to each message independently.\n*Agentic:* Given a goal, start a thread and iteratively create prompts and use tools in an attempt to fulfill the goal.",
                        },
                    },
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": "*Direct Messages*"},
                        "accessory": {
                            "type": "static_select",
                            "placeholder": {
                                "type": "plain_text",
                                "text": f"{current_mode.capitalize()}",
                            },
                            "initial_option": {
                                "text": {
                                    "type": "plain_text",
                                    "text": f"{current_mode.capitalize()}",
                                },
                                "value": f"{current_mode}",
                            },
                            "options": [
                                {
                                    "text": {"type": "plain_text", "text": "Direct"},
                                    "value": "direct",
                                },
                                {
                                    "text": {
                                        "type": "plain_text",
                                        "text": "Conversational",
                                    },
                                    "value": "conversational",
                                },
                                {
                                    "text": {"type": "plain_text", "text": "Agentic"},
                                    "value": "agentic",
                                },
                            ],
                            "action_id": "dm_mode_select",
                        },
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "_Changing modes outside of direct messages is not yet supported._",
                        },
                    },
                    {
                        "type": "context",
                        "elements": [
                            {"type": "mrkdwn", "text": f"Version *{VERSION}*"}
                        ],
                    },
                ],
            },
        )

    except Exception as e:
        logger.error(f"Error publishing home tab: {e}")


async def main():
    handler = AsyncSocketModeHandler(app, os.getenv("SLACK_APP_TOKEN"))
    await handler.start_async()


if __name__ == "__main__":
    asyncio.run(main())
