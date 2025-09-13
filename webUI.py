# 导入 Gradio 库，用于构建交互式前端界面
import gradio as gr
# 导入 requests 库，用于发送 HTTP 请求
import requests
# 导入 json 库，用于处理 JSON 数据
import json
# 导入 logging 库，用于记录日志
import logging
# 导入 re 库，用于正则表达式操作
import re
# 从 utils 模块导入 user_management，并重命名为 um
from utils import user_management as um
from utils.config import Config


# 设置日志的基本配置，指定日志级别为 INFO，并定义日志格式
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# 创建一个名为当前模块的日志记录器
logger = logging.getLogger(__name__)

# 定义后端服务接口的 URL 地址
url = f"http://{Config.HOST}:{Config.PORT}/v1/chat/completions"
# 定义 HTTP 请求头，指定内容类型为 JSON
headers = {"Content-Type": "application/json"}

# 是否流式输出
stream_flag = True # False

# 定义发送消息的函数，处理用户输入并获取后端回复
def send_message(user_message, history, user_id, conversation_id):
    # 构造发送给后端的数据，包含用户消息、用户 ID 和会话 ID
    data = {
        "messages": [{"role": "user", "content": user_message}],
        "stream": stream_flag,
        "userId": user_id,
        "conversationId": conversation_id
    }

    # 更新聊天历史，添加用户消息和临时占位回复
    history = history + [["user", user_message], ["assistant", "正在生成回复..."]]
    # 第一次 yield，返回当前的聊天历史和标题（标题暂不更新）
    yield history, history, None

    # 定义格式化回复内容的函数
    def format_response(full_text):
        # 将 <think> 标签替换为加粗的“思考过程”标题
        formatted_text = re.sub(r'<think>', '**思考过程**：\n', full_text)
        # 将 </think> 标签替换为加粗的“最终回复”标题
        formatted_text = re.sub(r'</think>', '\n\n**最终回复**：\n', full_text)
        # 返回去除前后空白的格式化文本
        return formatted_text.strip()

    # 流式输出
    if stream_flag:
        assistant_response = ""
        try:
            with requests.post(url, headers=headers, data=json.dumps(data), stream=True) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line:
                        json_str = line.decode('utf-8').strip("data: ")
                        if not json_str:
                            continue
                        if json_str.startswith('{') and json_str.endswith('}'):
                            try:
                                response_data = json.loads(json_str)
                                if 'delta' in response_data['choices'][0]:
                                    content = response_data['choices'][0]['delta'].get('content', '')
                                    assistant_response += content
                                    formatted_content = format_response(assistant_response)
                                    updated_history = history[:-1] + [["assistant", formatted_content]]
                                    yield updated_history, updated_history, None
                                if response_data.get('choices', [{}])[0].get('finish_reason') == "stop":
                                    break
                            except json.JSONDecodeError:
                                logger.error(f"JSON parsing error: {json_str}")
                                yield history[:-1] + [["assistant", "Error parsing response."]]
                                break
        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            yield history[:-1] + [["assistant", "Request failed. Please try again."]]

    # 非流式输出
    else:
        try:
            response = requests.post(url, headers=headers, data=json.dumps(data))
            response.raise_for_status()
            response_json = response.json()
            assistant_content = response_json['choices'][0]['message']['content']
            formatted_content = format_response(assistant_content)
            updated_history = history[:-1] + [["assistant", formatted_content]]
            yield updated_history, updated_history, None
        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            yield history[:-1] + [["assistant", "Request failed. Please try again."]]


# 定义获取会话列表的函数
def get_conversation_list(user_id):
    if not user_id:
        return ["Please select a conversation"]
    conv_list = um.get_conversation_list_for_user(user_id)
    # Format for dropdown: "Title - YYYY-MM-DD HH:MM:SS"
    return ["Please select a conversation"] + [f"{c['title']} - {c['created_at']}" for c in conv_list]

# 定义从选项中提取会话 ID 的函数
def extract_conversation_id_from_option(selected_option, user_id):
    if selected_option == "Please select a conversation" or not user_id:
        return None

    # Extract title and timestamp from the selected option
    try:
        title_part, timestamp_part = selected_option.rsplit(' - ', 1)
    except ValueError:
        return None # Or handle cases where the format is unexpected

    conv_list = um.get_conversation_list_for_user(user_id)
    for conv in conv_list:
        if conv['title'] == title_part and conv['created_at'] == timestamp_part:
            return conv['id']
    return None

# 使用 Gradio Blocks 创建前端界面
with gr.Blocks(title="Chat Assistant", css="""
    .login-container { max-width: 400px; margin: 0 auto; padding-top: 100px; }
    .modal { position: fixed; top: 20%; left: 50%; transform: translateX(-50%); background: white; padding: 20px; max-width: 400px; box-shadow: 0 4px 8px rgba(0,0,0,0.2); border-radius: 8px; z-index: 1000; }
    .chat-area { padding: 20px; height: 80vh; }
    .header { display: flex; justify-content: space-between; align-items: center; padding: 10px; }
    .header-btn { margin-left: 10px; padding: 5px 10px; font-size: 14px; }
""") as demo:
    # 定义状态变量
    logged_in = gr.State(False)
    current_user = gr.State(None)
    current_user_id = gr.State(None)
    current_conversation = gr.State(None)
    chatbot_history = gr.State([])
    conversation_title = gr.State("Create new chat")

    # 定义登录页面
    with gr.Column(visible=True, elem_classes="login-container") as login_page:
        gr.Markdown("## Chat Assistant")
        login_username = gr.Textbox(label="Username", placeholder="Enter username")
        login_password = gr.Textbox(label="Password", placeholder="Enter password", type="password")
        with gr.Row():
            login_button = gr.Button("Login", variant="primary")
            register_button = gr.Button("Register", variant="secondary")
        login_output = gr.Textbox(label="Result", interactive=False)

    # 定义聊天页面
    with gr.Column(visible=False) as chat_page:
        with gr.Row(elem_classes="header"):
            welcome_text = gr.Markdown("### Welcome,")
            with gr.Row():
                new_conv_button = gr.Button("New Chat", elem_classes="header-btn", variant="secondary")
                history_button = gr.Button("History", elem_classes="header-btn", variant="secondary")
                logout_button = gr.Button("Logout", elem_classes="header-btn", variant="secondary")

        with gr.Column(elem_classes="chat-area"):
            title_display = gr.Markdown("## Conversation Title", elem_id="title-display")
            chatbot = gr.Chatbot(label="Chat", height=450)
            with gr.Row():
                message = gr.Textbox(label="Message", placeholder="Enter message and press Enter", scale=8, container=False)
                send = gr.Button("Send", scale=2)

    # 定义注册弹窗
    with gr.Column(visible=False, elem_classes="modal") as register_modal:
        reg_username = gr.Textbox(label="Username", placeholder="Enter username")
        reg_password = gr.Textbox(label="Password", placeholder="Enter password", type="password")
        with gr.Row():
            reg_button = gr.Button("Submit", variant="primary")
            close_button = gr.Button("Close", variant="secondary")
        reg_output = gr.Textbox(label="Result", interactive=False)

    # 定义历史会话弹窗
    with gr.Column(visible=False, elem_classes="modal") as history_modal:
        gr.Markdown("### Conversation History")
        conv_dropdown = gr.Dropdown(label="Select a conversation", choices=["Please select a conversation"], value="Please select a conversation")
        load_conv_button = gr.Button("Load", variant="primary")
        close_history_button = gr.Button("Close", variant="secondary")

    # Helper functions for UI updates
    def show_register_modal(): return gr.update(visible=True)
    def hide_register_modal(): return gr.update(visible=False)
    def show_history_modal(user_id): return gr.update(visible=True), gr.update(choices=get_conversation_list(user_id), value="Please select a conversation")
    def hide_history_modal(): return gr.update(visible=False)
    def logout(): return False, None, None, None, gr.update(visible=True), gr.update(visible=False), "Logged out.", [], "Create new chat"
    def update_welcome_text(username): return gr.update(value=f"### Welcome, {username}")
    def update_title_display(title): return gr.update(value=f"## {title}")

    def login_and_load(username, password):
        success, uname, uid, cid, msg = um.login_user(username, password)
        if success:
            history = um.load_conversation_history(cid)
            title = "New Chat" # Title of the latest conversation on login
            return success, uname, uid, cid, msg, history, title
        return success, None, None, None, msg, [], "Create new chat"

    def new_conversation_ui(user_id):
        new_cid = um.create_new_conversation(user_id, "New Chat")
        return "New conversation created.", new_cid, [], "New Chat"

    def load_conversation_ui(selected_option, user_id):
        conv_id = extract_conversation_id_from_option(selected_option, user_id)
        if conv_id:
            history = um.load_conversation_history(conv_id)
            # Extract title from the option string
            title = selected_option.rsplit(' - ', 1)[0]
            return conv_id, history, title
        return None, [], "Create new chat"

    def update_history_and_title(chatbot_output, user_id, conv_id):
        if user_id and conv_id:
            # Persist history
            um.update_conversation_history(conv_id, chatbot_output)

            # Check if title needs to be set
            if len(chatbot_output) > 0:
                first_user_message = chatbot_output[0][1]
                new_title = first_user_message[:20] if len(first_user_message) > 20 else first_user_message
                um.update_conversation_title(conv_id, new_title)
                return chatbot_output, new_title
        return chatbot_output, "New Chat"


    # Event Listeners
    register_button.click(show_register_modal, None, register_modal)
    close_button.click(hide_register_modal, None, register_modal)
    reg_button.click(um.register_user, [reg_username, reg_password], reg_output)

    login_button.click(
        login_and_load,
        [login_username, login_password],
        [logged_in, current_user, current_user_id, current_conversation, login_output, chatbot_history, conversation_title]
    ).then(
        lambda logged: (gr.update(visible=not logged), gr.update(visible=logged)), [logged_in], [login_page, chat_page]
    ).then(
        update_welcome_text, [current_user], welcome_text
    ).then(
        lambda history: history, [chatbot_history], chatbot
    ).then(
        update_title_display, [conversation_title], title_display
    )

    logout_button.click(
        logout, None,
        [logged_in, current_user, current_user_id, current_conversation, login_page, chat_page, login_output, chatbot, conversation_title]
    )

    history_button.click(show_history_modal, [current_user_id], [history_modal, conv_dropdown])
    close_history_button.click(hide_history_modal, None, history_modal)

    new_conv_button.click(
        new_conversation_ui, [current_user_id], [login_output, current_conversation, chatbot, conversation_title]
    ).then(
        lambda: [], None, chatbot_history # Clear history state
    ).then(
        update_title_display, [conversation_title], title_display
    )

    load_conv_button.click(
        load_conversation_ui, [conv_dropdown, current_user_id], [current_conversation, chatbot, conversation_title]
    ).then(
        lambda history: history, [chatbot], chatbot_history # Update history state
    ).then(
        update_title_display, [conversation_title], title_display
    ).then(
        hide_history_modal, None, history_modal
    )

    # Chat message handling
    send_click_event = send.click(
        send_message,
        [message, chatbot_history, current_user_id, current_conversation],
        [chatbot, chatbot_history, conversation_title]
    ).then(
        update_history_and_title,
        [chatbot, current_user_id, current_conversation],
        [chatbot_history, conversation_title]
    ).then(
        update_title_display, [conversation_title], title_display
    ).then(
        lambda: "", None, message
    )

    message_submit_event = message.submit(
        send_message,
        [message, chatbot_history, current_user_id, current_conversation],
        [chatbot, chatbot_history, conversation_title]
    ).then(
        update_history_and_title,
        [chatbot, current_user_id, current_conversation],
        [chatbot_history, conversation_title]
    ).then(
        update_title_display, [conversation_title], title_display
    ).then(
        lambda: "", None, message
    )


# 如果当前脚本作为主程序运行，则启动 Gradio 应用
if __name__ == "__main__":
    # 启动 Gradio 应用，监听本地 7860 端口
    demo.launch(server_name="127.0.0.1", server_port=7860, share=True)