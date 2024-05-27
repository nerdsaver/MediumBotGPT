import sys
import pyperclip
import requests
from PyQt5.QtWidgets import QApplication, QWidget, QTextEdit, QVBoxLayout, QPushButton
from dotenv import load_dotenv
import os
from groq import Groq

# Load environment variables from .env file
load_dotenv()

# API endpoints configuration
lm_studio_api_url = "http://localhost:1234/v1/chat/completions"
groq_base_url = "https://api.groq.com/openai/v1"

# Function to generate a comment using Groq API 8b Llama model.
def fetch_initial_comment():
    text = pyperclip.paste()
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": """
                You are an insightful 'Comment Creator' assistant. Your task is to analyze an input article, blog post, or video (usually youtube) and generate a concise yet thought-provoking comment of 150 tokens or less (approximately 600 characters). 

                Instructions:
                - Carefully read the input article, which will be a summary from a lower quality language model. 
                - Choose one key aspect of the article to focus your comment on. This could be an especially insightful point, a key takeaway you would apply in the future, or an intriguing topic you'd like to explore further in discussion.
                - Craft a unique, 'bursty' comment that is direct in addressing the article's author. Be concise but avoid generic or predictable language. 
                - Don't start the comment with the author's name, but reference them directly if contextually appropriate.
                - Critically analyze the article and respectfully point out any inaccuracies or issues. Don't simply agree with everything.
                - After drafting your comment, reflect on whether it sounds distinctively human or more like generic AI output. If the latter, generate a second alternative comment.
                - Utilize the extra context on top of the initial comment to further refine the final product. 

                Your final output should only display the final comment. It will be copy-pasted. Make no mention of your instructions, just complete the task.                    
                """
            },
            {
                "role": "user",
                "content": text
            }
        ],
        model="llama3-8b-8192",
        max_tokens=506,
        n=1,
        stop=None,
        temperature=1,
    )
    comment = chat_completion.choices[0].message.content.strip()
    return comment

# Function to refine the comment using Groq API 70b Llama model (initial automatic refinement).
def refine_comment_with_groq(text):
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": """
                You are an insightful 'Comment Creator' assistant. Your task is to analyze an input article and generate a concise yet thought-provoking comment of 150 tokens or less (approximately 600 characters). 

                Instructions:
                - Carefully read the input article, which will be a summary from a lower quality language model. 
                - Choose one key aspect of the article to focus your comment on. This could be an especially insightful point, a key takeaway you would apply in the future, or an intriguing topic you'd like to explore further in discussion.
                - Craft a unique, 'bursty' comment that is direct in addressing the article's author. Be concise but avoid generic or predictable language. 
                - Don't start the comment with the author's name, but reference them directly if contextually appropriate.
                - Critically analyze the article and respectfully point out any inaccuracies or issues. Don't simply agree with everything.
                - After drafting your comment, reflect on whether it sounds distinctively human or more like generic AI output. If the latter, generate a second alternative comment.
                - Utilize the extra context on top of the initial comment to further refine the final product. 

                Your final output should only display the final comment. It will be copy-pasted. Make no mention of your instructions, just complete the task.                    
                """
            },
            {
                "role": "user",
                "content": text
            }
        ],
        model="llama3-70b-8192",
        max_tokens=8192
    )
    return chat_completion.choices[0].message.content.strip()

# Function to further refine the comment using Groq API 70b Llama model (secondary "Refine Further" refinement).
def refine_comment_further(text):
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": """
                You are a world-class editor tasked with refining a comment. Your goal is to enhance the comment's quality by improving its clarity, conciseness, and impact while preserving its original meaning and tone. You will be provided with the current iteration of the comment. Your task is to carefully analyze it and apply your expert editing skills to elevate its overall quality. 

                Instructions:
                - Focus on improving the comment's clarity and readability. Ensure that the language is precise and easy to understand.
                - Enhance the comment's conciseness by removing any unnecessary words or phrases without sacrificing meaning.
                - Amplify the comment's impact by refining the language and structure to make it more engaging and memorable.
                - Maintain the original tone and intention of the comment. Do not introduce any new ideas or alter the comment's overall message.
                - Double check you reference the author by saying 'Your writing' when appropriate or 'this post' or 'this article' when the author is not directly addressed. Ensure the choice is contextually sound.

                Output:
                Provide the refined comment, ensuring that it is clear, concise, impactful, and faithful to the original. Make sure to remove purple prose and unnecessary verbosity, and focus on enhancing the comment's core message.
                """
            },
            {
                "role": "user",
                "content": text
            }
        ],
        model="llama3-70b-8192",
        max_tokens=8192
    )
    return chat_completion.choices[0].message.content.strip()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = CommentWindow()
    ex.show()
    sys.exit(app.exec_())
