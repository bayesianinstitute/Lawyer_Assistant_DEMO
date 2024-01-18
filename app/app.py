from openai import OpenAI

import streamlit as st
import os
import time
import tempfile
import logging
from colorlog import ColoredFormatter
from PIL import Image

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = ColoredFormatter(
    "[ %(log_color)s%(levelname)s%(reset)s ] %(message)s",
    log_colors={
        'DEBUG': 'cyan',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'red,bg_white',
    }
)
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def init():
    st.session_state.setdefault("messages", [])
    st.session_state.setdefault("run", None)
    st.session_state.setdefault("file_ids", [])
    st.session_state.setdefault("thread_id", None)
    


def get_config():
    
    api_key = os.getenv("OPENAI_API_KEY")
    asst_id=os.getenv("Assist_id")

    # Check if the API key is present
    if not api_key :
        raise ValueError("API key not found in the .env file")
    elif not asst_id:
        raise ValueError("Assist_id not found in the .env file")

    return api_key,asst_id


def assistant_handler(client, assistant_id):
    
    assistant = client.beta.assistants.retrieve(assistant_id)
    model_option='gpt-4-1106-preview'
    assistant_instructions=assistant.instructions
    file_ids=assistant.file_ids

    return assistant, model_option, assistant_instructions,file_ids

def check_run_status(client, thread_id, run_id):
    # Check Run Status
    run = client.beta.threads.runs.retrieve(run_id=run_id, thread_id=thread_id)
    
    return run.status
             
def chat_prompt(client, assistant_id):
    if prompt := st.chat_input("Enter your message here"):
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.messages = st.session_state.messages.append(client.beta.threads.messages.create(
            thread_id=st.session_state.thread_id,
            role="user",
            content=prompt,
        ))

        st.session_state.current_assistant = client.beta.assistants.update(
            st.session_state.current_assistant.id,
            instructions=st.session_state.assistant_instructions,
            name=st.session_state.current_assistant.name,
            tools = st.session_state.current_assistant.tools,
            model=st.session_state.model_option,
            file_ids=st.session_state.file_ids,
        )


        st.session_state.run = client.beta.threads.runs.create(
            thread_id=st.session_state.thread_id,
            assistant_id=assistant_id,
            

        )
        
        logging.debug(f"Run_Status : {st.session_state.run.status}")
        pending = False
        while st.session_state.run.status != "completed":
            if not pending:
                with st.chat_message("assistant"):
                    st.markdown("AnalAssist is thinking...")
                pending = True
            time.sleep(3)
            st.session_state.run = client.beta.threads.runs.retrieve(
                thread_id=st.session_state.thread_id,
                run_id=st.session_state.run.id,
            )
            
             
                    
        if st.session_state.run.status == "completed": 
            st.empty()
            chat_display(client)

def chat_display(client):
    st.session_state.messages = client.beta.threads.messages.list(
        thread_id=st.session_state.thread_id
    ).data

    for message in reversed(st.session_state.messages):
        if message.role in ["user", "assistant"]:
            with st.chat_message(message.role):
                for content in message.content:
                    if content.type == "text":
                        st.markdown(content.text.value)
                    elif content.type == "image_file":
                        image_file = content.image_file.file_id
                        image_data = client.files.content(image_file)
                        image_data = image_data.read()
                        #save image to temp file
                        temp_file = tempfile.NamedTemporaryFile(delete=False)
                        temp_file.write(image_data)
                        temp_file.close()
                        #display image
                        image = Image.open(temp_file.name)
                        st.image(image)
                    else:
                        st.markdown(content)
                    

def main():
    st.title('Lawyer Assistant')
    st.divider()
    api_key,assistant_id = get_config()
    client = OpenAI(api_key=api_key)
    st.session_state.current_assistant, st.session_state.model_option, st.session_state.assistant_instructions,st.session_state.file_ids = assistant_handler(client, assistant_id)
    if st.session_state.thread_id is None:
        st.session_state.thread_id = client.beta.threads.create().id
        logging.info(f"Thread-ID : {st.session_state.thread_id}")
    chat_prompt(client, assistant_id)
            



if __name__ == '__main__':
    init()
    main() 
    logging.info(f"File ID: {st.session_state.file_ids}")


