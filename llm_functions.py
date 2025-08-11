from modal.cli.app import history

import file_management_base
import email_body_extractor
import google.generativeai as gen
from google import genai
from google.genai import types
from dotenv import load_dotenv
import json
import os
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import re
import logging

logger,service,apikey,client=None,None,None,None
def initialize():
    global logger,service,apikey,client
    logger = logging.getLogger(__name__)
    service = file_management_base.authenticate_and_return_service()

    load_dotenv(override=True)
    apiKey = os.getenv('GEMINI_API_KEY')
    # The client gets the API key from the environment variable `GEMINI_API_KEY`.
    client = genai.Client(api_key=apiKey)
    gen.configure(api_key=apiKey)


def parse_list_string(s):
    s = s.strip()

    # Replace only first and last char if they're not normal quotes
    if s and s[0] not in ['[',']']:
        s = s[1:]
    if s and s[-1] not in ['[',']']:
        s = s[:-1]
    return s
def safe_extract_assistant_text(response):
    # Try multiple places where assistant text might live
    try:
        # genai responses: response.candidates[0].content[0].text
        cand = response.candidates[0]
        # try various shapes:
        if hasattr(cand, "content"):
            cont = cand.content
            # cont can be list or object with parts
            if isinstance(cont, list) and len(cont) > 0 and hasattr(cont[0], "text"):
                return cont[0].text
            if hasattr(cont, "text"):
                return cont.text
            if hasattr(cont, "parts"):
                for p in cont.parts:
                    if isinstance(p, dict) and p.get("text"):
                        return p["text"]
        # fallback to str(response)
        return str(response)
    except Exception:
        return None

def initialize_gemini_model(chat_history=[]):
    system_prompt = ""
    with open("static/system_prompt_main_llm.txt", "r", encoding="utf-8") as prompt:
        system_prompt = prompt.read()

    model = gen.GenerativeModel(
        model_name='gemini-2.5-flash',
        tools=list(tool_registry.values()),
        system_instruction=system_prompt,# Pass the function objects themselves
        safety_settings={
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }
    )

    return model.start_chat(history=chat_history)

# this is a tool for llm
#Write the most current hierarchy structure
def reload_hierarchy():
    """
    updates the hierarchy.txt file to map the latest updates of actual google drive
    use this function to pull out latest updates from database
    :return True if succesfully executed , False if fails:
    """
    with open("static/hierarchy.txt", "w", encoding="utf-8") as f:
        file_management_base.list_items_recursively(service,file_management_base.find_shared_folder_id(service,file_management_base.TARGET_FOLDER_NAME),f=f)
    return True

def request_hierarchy_contents():
    '''
    only and only use this function if user specifically use $$DEBUG$$ tag at staring and requesting to view or show hierarchy contents
    :return: hierarchy raw text data
    '''
    with open("static/hierarchy.txt", "r", encoding="utf-8") as f:
        return f.read()

# this is a tool for llm
def request_files_for_context(user_prompt:str):
    """Retrieves internal contextual documents to help the LLM answer user queries about the university.

    This tool searches an official database for up-to-date, factual information. It is the authoritative source for topics such as:
    - **Campus Navigation:** Directions, building locations, room numbers, and campus maps.
    - **Academic Information:** Course syllabi, detailed course information, academic schedules, and timetables.
    - **Campus Life & Details:** Information about facilities, departments, and general university life.

    **Crucial Guideline:** The output of this function is raw text from internal documents and is intended for the LLM's use as context only. **NEVER** show the raw output of this function directly to the user. You must process and synthesize the information provided by this tool to generate a helpful and coherent answer in your own words.

    :param user_prompt: The user's original query. This is used to find the most relevant documents.
    :return: A list of strings, where each string is a relevant text chunk from the knowledge base. This data is for internal LLM consumption and is not intended for the user.
    """
    system_prompt = ""
    with open("static/system_prompt_rag.txt", "r", encoding="utf-8") as f:
        system_prompt = f.read()
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            system_instruction=system_prompt),
        contents=[user_prompt,request_hierarchy_contents()]
    )
    print(parse_list_string(response.text))
    file_paths=json.loads(parse_list_string(response.text))
    return [
        file_management_base.get_upload_ready_file_for_llm(file_management_base.get_file_name_from_id(service,fileid),file_management_base.download_file_content(service,fileid))
        for fileid in [file_management_base.get_file_id_from_path(service,path) for path in file_paths]
    ]


# this is a tool for llm
def request_files_id_2sharable_link_gemini_rag(user_prompt:str):
    """Provides direct, sharable download links for files requested by the user.

    Call this function ONLY when the user explicitly requests a downloadable file, such as notes, documents, or syllabi. It is triggered by phrases like:
    Direct Requests
        Send me the presentation slides.
        Get me the PDF for chapter 5.
        Forward me the email with the attachment.
        Shoot me the document when you have a second. (informal)
    Polite Questions
        Could you send the files for the marketing campaign?
        Do you have the notes from yesterday's lecture?
        Would you mind sharing the report with me?
        Is it possible to get a copy of the contract?
    Statements of Need
        I'm looking for the project requirements document.
        I need the syllabus for Chemistry 202.
        I'm trying to find the reading list for this semester.
        I'd like to get the resources mentioned in class.
        Can I get the link to the shared drive?
        Could you drop the link for the Zoom meeting in the chat? (informal)
        Where can I find the link to the submission portal?
        What's the URL for the resource page?

    **Crucial Guideline:** The links returned by this function are for the **USER**, not the LLM. You should present these links directly to the user in your response. This tool does NOT provide context for generating answers.

    :param user_prompt: The file request, which must be prefixed with the '$$REQUEST-FILE$$' tag.
                       Example: "$$REQUEST-FILE$$ notes for maths semester 1 hyperbolic functions"
    :return: A list of sharable URL strings for the files requested by the user. Returns an empty list if no files are found.
    """
    system_prompt = ""
    with open("static/system_prompt_rag_request_file.txt", "r", encoding="utf-8") as f:
        system_prompt = f.read()

    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        config=types.GenerateContentConfig(
            system_instruction=system_prompt),
        contents=[user_prompt,request_hierarchy_contents()]
    )
    file_paths = json.loads(parse_list_string(response.text))
    print(file_paths)
    ids = [file_management_base.get_file_id_from_path(service, path) for path in file_paths]
    print(ids)
    return [file_management_base.create_sharable_link(service,id) for id in ids]





# gemini response core block
def _extract_candidates(response):
    """Return a list-like of candidates or None."""
    try:
        if hasattr(response, "result") and hasattr(response.result, "candidates"):
            return response.result.candidates
        if hasattr(response, "candidates"):
            return response.candidates
        if isinstance(response, dict) and "candidates" in response:
            return response["candidates"]
    except Exception:
        logger.debug("Could not read candidates from response", exc_info=True)
    return None

def _extract_text_from_candidate(c):
    """Try multiple shapes to extract assistant text from a candidate."""
    try:
        # protobuf-like: content.parts[0].text
        if hasattr(c, "content"):
            cont = c.content
            if hasattr(cont, "parts") and cont.parts:
                part = cont.parts[0]
                if isinstance(part, dict):
                    return part.get("text")
                elif hasattr(part, "text"):
                    return part.text
            if hasattr(cont, "text"):
                return cont.text
            if isinstance(cont, list) and len(cont) > 0:
                first = cont[0]
                if isinstance(first, dict):
                    return first.get("text")
                elif hasattr(first, "text"):
                    return first.text
        # dict-like candidate:
        if isinstance(c, dict):
            cont = c.get("content")
            if isinstance(cont, dict):
                parts = cont.get("parts")
                if parts and isinstance(parts, list) and len(parts) > 0:
                    p = parts[0]
                    if isinstance(p, dict):
                        return p.get("text")
                return cont.get("text")
    except Exception:
        logger.debug("Failed to extract text from candidate", exc_info=True)
    return None

def _extract_function_call_from_candidate(c):
    """Try multiple shapes to extract function_call (dict or object)."""
    try:
        # candidate.content.parts[0].function_call
        if hasattr(c, "content"):
            cont = c.content
            if hasattr(cont, "parts") and cont.parts:
                part = cont.parts[0]
                if isinstance(part, dict) and "function_call" in part:
                    return part.get("function_call")
                elif hasattr(part, "function_call"):
                    return part.function_call
            if isinstance(cont, list) and len(cont) > 0:
                first = cont[0]
                if isinstance(first, dict) and "function_call" in first:
                    return first["function_call"]
                elif hasattr(first, "function_call"):
                    return first.function_call
        # sometimes candidate itself has function_call
        if hasattr(c, "function_call"):
            return c.function_call
        if isinstance(c, dict) and "function_call" in c:
            return c["function_call"]
    except Exception:
        logger.debug("Failed to extract function_call", exc_info=True)
    return None

def _parse_arguments(raw_args):
    """Turn raw_args into a dict in a tolerant way."""
    if not raw_args:
        return {}
    # already a dict-like
    if isinstance(raw_args, dict):
        return raw_args
    # string -> try json
    if isinstance(raw_args, str):
        try:
            return json.loads(raw_args)
        except Exception:
            # try simple normalization (single quotes -> double quotes)
            try:
                return json.loads(raw_args.replace("'", '"'))
            except Exception:
                # Try to extract a {...} substring and parse
                m = re.search(r"(\{.*\})", raw_args, flags=re.S)
                if m:
                    try:
                        return json.loads(m.group(1).replace("'", '"'))
                    except Exception:
                        pass
        # as last resort, return an empty dict so we can still call the tool without args
        return {}
    # list/tuple of pairs or object convertible to dict
    try:
        return dict(raw_args)
    except Exception:
        return {}

def gemini_main_response(user_prompt: str, gemini_chat):
    """
    Sends the user prompt to gemini_chat, handles an optional function_call,
    executes the selected function (if valid) with selected_function(**dict(args)),
    sends the function result back to the model as a tool-like message,
    and finally returns the model's final assistant text (string).
    """
    # 1) initial model call
    response = gemini_chat.send_message(user_prompt)

    # 2) extract candidates and primary candidate
    candidates = _extract_candidates(response)
    if not candidates or len(candidates) == 0:
        # Nothing parsed: return a readable fallback
        return str(response)

    cand0 = candidates[0]

    # 3) extract assistant text (may be used as fallback)
    assistant_text = _extract_text_from_candidate(cand0)

    # 4) extract possible function_call
    function_call = _extract_function_call_from_candidate(cand0)

    # 5) if model returned a function_call, validate and attempt to run it
    if function_call:
        # normalize name and args
        if isinstance(function_call, dict):
            fname = function_call.get("name")
            raw_args = function_call.get("arguments")
        else:
            fname = getattr(function_call, "name", None)
            raw_args = getattr(function_call, "arguments", None)

        # guard: empty or whitespace-only name -> treat as NO_TOOL
        if not (isinstance(fname, str) and fname.strip()):
            logger.info("Model returned empty/whitespace function name -> falling back to assistant text.")
            return assistant_text or "I couldn't parse the model's response; please rephrase."

        # ensure the tool exists
        if fname not in tool_registry:
            logger.info("Model requested unknown function '%s' -> falling back to assistant text.", fname)
            return assistant_text or f"Model requested unknown function: {fname}"

        # parse args as a dict (we keep the behavior you requested)
        args_dict = function_call.args
        print(f'calling function {fname} with arguments {args_dict}')

        # Call the selected function using **dict(args) pattern the project expects.
        try:
            selected_function = tool_registry[fname]
            # ensure we pass a plain dict to satisfy selected_function(**dict(args))
            # This will raise a TypeError if selected_function doesn't accept kwargs — let it propagate to be handled below.
            tool_result = selected_function(**dict(args_dict))
        except TypeError as te:
            logger.exception("TypeError while calling tool %s with args %r", fname, args_dict)
            return f"Error: tool '{fname}' could not be called with provided arguments: {te}"
        except Exception as e:
            logger.exception("Exception while running tool %s", fname)
            return f"Error running tool {fname}: {e}"

        # --- SEND THE RESULT BACK TO THE MODEL ---
        # Use the exact structure you provided so the model can consume it as tool output.
        func_resp_content = {
            "role": "tool",
            "parts": [
                {
                    "function_response": {
                        "name": fname,
                        "response": {"tool_result": tool_result}
                    }
                }
            ]
        }

        # send the tool response back to the model; the model will generate the final text reply
        # (wrap in list for consistency with how you call send_message)
        final_response = gemini_chat.send_message(func_resp_content)

        # parse final_response and return final assistant text
        final_cands = _extract_candidates(final_response)
        if final_cands and len(final_cands) > 0:
            final_text = _extract_text_from_candidate(final_cands[0])
            return final_text or str(final_response)
        else:
            return str(final_response)

    # 6) no function_call -> return assistant_text (final answer)
    return assistant_text or str(response)
#block ends



def tool_reload_announcements():
    """
    reloads the announcements file , pulls out the latest announcements from database
    :return:
    """
    with open("static/announcements.txt", "w", encoding="utf-8") as f:
        for email in email_body_extractor.read_emails_with_subject_alternative():
            print(f"announcement : {email}",file=f,end="")


# this is a llm tool
def read_announcements(howMany=10):
    """
    returns a list of the latest announcements
    :return: list of announcements
    """
    tool_reload_announcements()
    announcements = ""
    with open("static/announcements.txt", "r", encoding="utf-8") as f:
        announcements = f.readlines()
    while "\n"in announcements:
        announcements.remove("\n")
    return list(reversed(announcements))[:howMany]


tool_registry = {
    "request_files_id_2sharable_link_gemini_rag": request_files_id_2sharable_link_gemini_rag,
    "reload_hierarchy": reload_hierarchy,
    "read_announcements":read_announcements,
    "request_files_for_context":request_files_for_context,
    "request_hierarchy_contents":request_hierarchy_contents
}
'''debug testing here '''
# reload_hierarchy()
# gemini_chat = initialize_gemini_model()
# user_prompt = "what are washrooms?"
# print(gemini_main_response(user_prompt, gemini_chat))
# tool_reload_announcements()
# print(tool_read_announcements())
#gemini_rag_id_2file("what is the syllabus of maths semister 1")

