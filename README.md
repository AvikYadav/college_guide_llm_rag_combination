🎓 Campus Compass: The Intelligent RAG Assistant
An intelligent, user-friendly Retrieval-Augmented Generation (RAG) system designed to be the ultimate campus companion. It hooks directly into a Google Drive folder, allowing for an incredibly easy-to-update knowledge base, and uses a powerful LLM to answer student queries accurately.

✨ Key Features
🧠 Intelligent RAG System: Utilizes a sophisticated two-step process. First, it intelligently gathers relevant context from documents, and second, it uses that context to extract a precise, helpful answer for the user.

📂 Google Drive as a Database: The entire knowledge base is a simple Google Drive folder. Updating information is as easy as dragging and dropping files. No complex database management needed!

🏷️ Smart File Tagging: Use special tags like $$SYSTEM$$ and $$USER-NOTES$$ in your filenames to define their roles, helping the RAG system prioritize official documents over user-contributed notes when needed.

📢 Real-time Announcements: A moderator can send an email with the subject line "announcements" to a dedicated email address, and the system can fetch and display these updates instantly.

🤖 LLM-Powered: Leverages the power of Large Language Models (we're using Google's Gemini for now) to understand queries and provide conversational, accurate answers.

⚙️ How It Works
The system is built around a simple yet powerful architecture that makes it both effective and easy to maintain.

1. The Knowledge Base (Google Drive)
The core of the system is a shared Google Drive folder. You create a folder hierarchy that makes sense for your institution. The RAG system intelligently scans this structure.

You can tag files to give the system hints about their content:

$$SYSTEM$$: Marks official documents (e.g., syllabi, maps, official rules). These are often treated as the "source of truth."

$$USER-NOTES$$: Marks user-contributed content, like student lecture notes.

$$USER-BOOK$$: Marks textbook files.

Here is an example of a folder structure:

NSUT/
├── $$SYSTEM$$:timetable_lectureHalls_faculties.json
├── about_clg/
│   ├── $$SYSTEM$$:Complete_Detailed_Campus_Map_and_Infrastructure.pdf
│   └── $$SYSTEM$$:Navigation_instructions_rules_must_be_followed.txt
├── books/
│   └── maths/
│       └── hyperbolic functions/
│           └── $$USER-BOOK$$:hyperbolic_functions_by_james_mcMahon.pdf
├── cad_or_engneeringDrawing/
│   └── semister1/
│       ├── $$SYSTEM$$Syllabus-Scanned-1.pdf
│       ├── $$USER-NOTES$$tonve cad lecture 1.pdf
│       └── $$USER-NOTES$$hitesh cad lecture 1.pdf
└── maths/
    └── semister 1/
        ├── $$SYSTEM$$Syllabus.pdf
        └── $$USER-NOTES$$:Maths-intoduction to hyperbolic func lecture 1.pdf

2. LLM Capabilities (Tools)
The Large Language Model is given specific tools to interact with the knowledge base and perform tasks:

Request Files for Context: Looks up information from official university documents on topics like campus navigation, academic information, and campus life to answer questions accurately.

Request Sharable File Links: Provides a direct, shareable download link for a specific document, notes, or syllabus.

Read Announcements: Fetches and displays the latest announcements sent via the dedicated email channel.

🚀 Getting Started
Follow these steps to set up and run your own instance of the Campus Compass assistant.

Prerequisites
Python 3.9+

A Google Cloud Platform project

A dedicated Gmail account for announcements

1. Clone the Repository
git clone https://github.com/your-username/your-repo-name.git
cd your-repo-name

2. Install Dependencies
pip install -r requirements.txt

(Note: You will need to create a requirements.txt file with all the necessary libraries like google-api-python-client, google-auth-httplib2, google-auth-oauthlib, python-dotenv, google-generativeai, etc.)

3. Configure Google Drive & Service Account
This system uses a Service Account to access Google Drive files without needing manual user login.

Go to the Google Cloud Console.

Create a new project or select an existing one.

Enable the Google Drive API.

Go to "Credentials," click "Create Credentials," and select "Service account."

Follow the steps to create the account. Grant it the "Viewer" role at a minimum.

After creation, go to the "Keys" tab for the service account, click "Add Key," and create a new JSON key.

A .json file will be downloaded. Rename this file to service-account.json and place it in the root directory of this project.

Most Importantly: You must share your Google Drive folder (the one containing all the documents) with the service account's email address (e.g., my-service-account@my-project.iam.gserviceaccount.com).

4. Set Up Environment Variables
Create a file named .env in the root directory of the project. This file will store your secret keys.

# .env file

# API Key for the LLM (Google Gemini)
GEMINI_API_KEY="YOUR_GEMINI_API_KEY"

# Gmail account for fetching announcements
GMAIL="your-announcement-email@gmail.com"

# Gmail App Password for the account (do not use your regular password)
# See: https://support.google.com/accounts/answer/185833
GMAIL_PASS="your_gmail_app_password"

5. Run the Application
python app.py

Now you can start asking the Campus Compass questions!

💡 Example Use Cases
Navigation: "Where can I find the main library?"

Resource Finding: "Can you give me the link to the syllabus for Electrical Engineering?"

Notes Retrieval: "Find me Hitesh's notes for the first CAD lecture."

Stay Updated: "Are there any new announcements?"
