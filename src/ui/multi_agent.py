import os
import re
import asyncio
import subprocess
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.agents import AgentGroupChat, ChatCompletionAgent
from semantic_kernel.agents.strategies.termination.termination_strategy import TerminationStrategy
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.agents import AgentGroupChat
from semantic_kernel.functions import KernelFunctionFromPrompt
from semantic_kernel.agents.strategies import (
    KernelFunctionSelectionStrategy,
    KernelFunctionTerminationStrategy,
)
from semantic_kernel.contents import ChatHistoryTruncationReducer
from semantic_kernel.contents import ChatMessageContent
from semantic_kernel.agents.agent import Agent
from semantic_kernel.contents import FunctionCallContent, FunctionResultContent
from semantic_kernel.agents.chat_completion.chat_completion_agent import ChatCompletionAgent, ChatHistoryAgentThread
from dotenv import load_dotenv
import streamlit as st
from semantic_kernel.agents.strategies import KernelFunctionSelectionStrategy
load_dotenv()
kernel = Kernel()
kernel.add_service(
    AzureChatCompletion(
        service_id="default",
        deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),  # Example: "gpt-4"
        endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    )
)

# 3. Define Persona Instructions
business_analyst_instructions = """
You are a Business Analyst which will take the requirements from the user (also known as a 'customer') and create a project plan for creating the requested app. The Business Analyst understands the user requirements and creates detailed documents with requirements and costing. The documents should be usable by the SoftwareEngineer as a reference for implementing the required features, and by the Product Owner for reference to determine if the application delivered by the Software Engineer meets all of the user's requirements."""

software_engineer_instructions = """
You are a Software Engineer, and your goal is create a web app using HTML and JavaScript by taking into consideration all the requirements given by the Business Analyst. The application should implement all the requested features. Deliver the code to the Product Owner for review when completed. You can also ask questions of the BusinessAnalyst to clarify any requirements that are unclear. """

product_owner_instructions = """
You are the Product Owner which will review the software engineer's code to ensure all user  requirements are completed. You are the guardian of quality, ensuring the final product meets all specifications. IMPORTANT: Verify that the Software Engineer has shared the HTML code using the format ```html [code] ```. This format is required for the code to be saved and pushed to GitHub. Once all client requirements are completed and the code is properly formatted, reply with 'READY FOR USER APPROVAL'. If there are missing features or formatting issues, you will need to send a request back to the SoftwareEngineer or BusinessAnalyst with details of the defect."""
BusinessAnalyst="BusinessAnalyst"
SoftwareEngineer="SoftwareEngineer"
ProductOwner="ProductOwner"

class ApprovalTerminationStrategy(TerminationStrategy):
    async def should_agent_terminate(self,agent: Agent, history: list[ChatMessageContent]) -> bool:
        """Check if the conversation should terminate based on the Product Owner's approval."""
        for message in history:
            print("Querying inside message")
            if message.content.upper()=="APPROVED":
                pushGtoGit()
                return True
        return False
    
business_analyst = ChatCompletionAgent(
    kernel=kernel,
    name=BusinessAnalyst,
    instructions=business_analyst_instructions
    )
software_engineer = ChatCompletionAgent(
    kernel=kernel,
    name="SoftwareEngineer",
    instructions=software_engineer_instructions
    )

product_owner = ChatCompletionAgent(
    kernel=kernel,
    name="ProductOwner",
    instructions=product_owner_instructions
    )
selection_function = KernelFunctionFromPrompt(
        function_name="selection",         
        prompt=f"""Determine which participant takes the next turn in a conversation based on the most recent participant's message.  
                Only return the name of the participant.
                Never choose the participant named in the RESPONSE.

                Participants:  
                - BusinessAnalyst  
                - SoftwareEngineer  
                - ProductOwner

                Rules:               
                - The first turn is always the BusinessAnalyst.
                - After the user inputs a requirement, it's the BusinessAnalyst turn.
                - After the BusinessAnalyst responds, the SoftwareEngineer should convert the requirement into HTML.
                - After the SoftwareEngineer provides HTML, the ProductOwner should validate it.
                - If ProductOwner approves  with "READY FOR USER APPROVAL", the conversation ends.
                - If not approved, the next turn goes to SoftwareEngineer to correct.
                

                
                History:  
                {{{{ $history }}}}
                
                """)
termination_keyword = "APPROVED"
termination_function = KernelFunctionFromPrompt(
        function_name="termination",
        prompt="""
        Determine if the copy has been approved.  If so, respond with a single word: READY FOR USER APPROVAL
        History:
        {{{{ $history }}}}
        """,
    )
def agent_response_callback(message: ChatMessageContent) -> None:
    """Observer function to print the messages from the agents."""
    print("I am inside agent response call back function 108")
    #print(f"**{message.name}**\n{message.content}")
#from semantic_kernel.agents.strategies import KernelFunctionSelectionStrategy
env_vars = {
    "GITHUB_USERNAME": os.getenv("GITHUB_USERNAME"),
    "GITHUB_REPO": os.getenv("GITHUB_REPO"),
    "GITHUB_PAT": os.getenv("GITHUB_PAT"),
    "GITHUB_REPO_URL":os.getenv("GITHUB_REPO_URL"),
    "GIT_USER_EMAIL":os.getenv("GIT_USER_EMAIL")
}


def pushGtoGit():              
        env = {**os.environ,**env_vars}
        current_file_path = os.path.abspath(__file__)
# Go one level up to get the project root
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file_path)))        
        script_path = os.path.join( project_root, "pushtoGitFolder", "push_to_github.sh")
        bash_path = r"C:\Program Files\Git\bin\bash.exe"
        try:
            result = subprocess.run([bash_path, script_path], check=True, capture_output=True, text=True, env=env)
            print("Script output:\n", result.stdout)
        except subprocess.CalledProcessError as e:
            print("Script failed:\n", e.stderr)

    
async def run_multi_agent(usermessage, group_chat=None):  
    history_reducer = ChatHistoryTruncationReducer(target_count=10)
    if group_chat is None:
        group_chat = AgentGroupChat(
        agents=[business_analyst, software_engineer, product_owner],   
        selection_strategy=KernelFunctionSelectionStrategy(
            initial_agent=business_analyst,
            function=selection_function,
            kernel=kernel,  
            result_parser=lambda result: str(result).strip() ,         
            history_variable_name="history",
            history_reducer=history_reducer,
            termination_keyword="APPROVED"
        )    , 
        termination_strategy = ApprovalTerminationStrategy() 
        )

    is_complete = False 
    print(usermessage)
    user_input=usermessage   
    chat_messages = []        
    await group_chat.add_chat_message(message=user_input)
    if user_input.strip().upper() != "APPROVED":
        group_chat.is_complete=False    
    results = []
    try:
        
        async for result in group_chat.invoke():
            st.markdown(f"**{result.role} - {result.name or '*'}**")
            st.info(result.content)
            chat_messages.append(result)  
            if result is None or not result.name:
                #return result              
                continue     
            if "READY FOR USER APPROVAL" in result.content.upper():
                print("Product Owner is ready for user approval.")
                #group_chat.is_complete=True
                st.success("Product Owner is ready for user approval.")
                #st.markdown("**Please click on the button below to approve the changes.**")
                #st.button("Approve", on_click=pushGtoGit)
                html_code = None
                for msg in reversed(chat_messages):
                    if msg.name == "SoftwareEngineer":
                        match = re.search(r"```html(.*?)```", msg.content, re.DOTALL | re.IGNORECASE)
                        if match:
                            html_code = match.group(1).strip()                            

                        if html_code:
                            print("✅ Extracted HTML code:\n", html_code)
                            # You can also display this in Streamlit
                            #st.code(html_code, language='html')
                        else:
                            print("⚠️ No HTML code found from Software Engineer.")
                        if html_code:        # Define path
                            folder_path = os.path.join(os.getcwd(), "pushtoGitFolder")
                            os.makedirs(folder_path, exist_ok=True)
                            file_path = os.path.join(folder_path, "index.html")
                            current_file_path = os.path.abspath(__file__)
                            # Go one level up to get the project root
                            project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file_path)))        
                            script_path = os.path.join( project_root, "pushtoGitFolder", "index.html")
                            # Save the HTML file
                            with open(script_path, "w", encoding="utf-8") as f:
                                f.write(html_code)
                            print(f"✅ HTML code saved to {file_path}")
                            # st.success("HTML file saved successfully to pushtoGitFolder/index.html")
                            # st.code(html_code, language='html')
                            break
                        else:
                            print("⚠️ No HTML code found from Software Engineer.")
                return group_chat
                break
                #return group_chat       
            if group_chat.is_complete:
                st.success("Conversation completed!")
                break
    except Exception as e:
            print(f"Error during chat invocation: {e}")    


