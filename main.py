from r2r import R2RAsyncClient
import os
import json
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
import re

load_dotenv()

class R2RChatbot:
    """
    R2R Async Chatbot class for handling job applications portfolio interactions.
    """
    
    def __init__(self, user_id, api_key=None, base_url="https://api.sciphi.ai"):
        """
        Initialize R2R Async Chatbot.
        
        Args:
            api_key: R2R API key (optional, can be set via environment variable)
            base_url: R2R API base URL
        """
        self.client = self._initialize_client(api_key, base_url)
        self.document_id = None
        self.conversation_id = None
        self.document_path = f"docs/job_applications_user_{user_id}.md"
    
    def _initialize_client(self, api_key=None, base_url="https://api.sciphi.ai"):
        """Initialize R2R async client with proper authentication"""
        try:
            # Option 1: Use local R2R instance (if you have one running)
            # client = R2RAsyncClient(base_url="http://localhost:7272")
            
            # Option 2: Use SciPhi Cloud (requires API key)
            api_key = api_key or os.getenv("R2R_API_KEY")
            if api_key:
                client = R2RAsyncClient(base_url=base_url)
                # You may need to login if using cloud
                # await client.users.login(email="your_email", password="your_password")
                return client
            else:
                print("Warning: No R2R_API_KEY found in environment variables")
                return None
        except Exception as e:
            print(f"Error initializing R2R async client: {e}")
            return None
    
    def generate_application_document(self, applications_data, questions_data):
        """
        Generate a well-formatted document from applications and questions JSON data.
        
        Args:
            applications_data: Dictionary containing job applications data
            questions_data: Dictionary containing questions and answers data
            output_filename: Name of the output document file
        """
        
        # Create a mapping of applicationId to questions for quick lookup
        questions_by_app_id = {}
        if 'items' in questions_data:
            for question in questions_data['items']:
                app_id = question['applicationId']
                if app_id not in questions_by_app_id:
                    questions_by_app_id[app_id] = []
                questions_by_app_id[app_id].append(question)
        
        # Start building the document content
        document_content = []
        document_content.append("# Job Applications Portfolio")
        document_content.append(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        document_content.append("-" * 3)
        document_content.append("")
        
        # Add summary statistics
        total_applications = len(applications_data.get('items', []))
        document_content.append(f"## Summary")
        document_content.append(f"Total Applications: {total_applications}")
        document_content.append(f"Total Questions Answered: {questions_data.get('totalCount', 0)}")
        document_content.append("")
        document_content.append("-" * 3)
        document_content.append("")
        
        # Process each application
        for i, application in enumerate(applications_data.get('items', []), 1):
            app_id = application['applicationId']
            
            # Application Header
            document_content.append(f"## APPLICATION {i}: {application['jobTitle']} at {application['companyName']}")
            # document_content.append("-" * 3)
            document_content.append("")
            
            # Basic Application Information
            document_content.append("### Basic Information")
            document_content.append(f"• Application ID: {app_id}")
            document_content.append(f"• Job Title: {application['jobTitle']}")
            document_content.append(f"• Job Type: {application['jobType']}")
            document_content.append(f"• Company: {application['companyName']}")
            document_content.append(f"• Location: {application['company']['location']}")
            document_content.append(f"• Application Status: {application['status']}")
            document_content.append(f"• Current Stage: {application['stage']}")
            document_content.append(f"• Submission Date: {application['submissionDate']}")
            
            # ATS Score
            if application.get('atsScore') is not None:
                document_content.append(f"• ATS Score: {application['atsScore']}/100")
            else:
                document_content.append("• ATS Score: Not available")
            document_content.append("")
            
            # Company Details
            document_content.append("### Company Details")
            company = application['company']
            document_content.append(f"• Company Name: {company['name']}")
            document_content.append(f"• Location: {company['location']}")
            document_content.append(f"• Careers Website: {company['careersLink']}")
            document_content.append(f"• LinkedIn: {company['linkedinLink']}")
            document_content.append("")
            
            # Job Description
            document_content.append("### Job Description")
            job_description = application.get('description', 'No description available')
            # Format the job description for better readability
            if len(job_description) > 100:
                document_content.append(f"```")
                document_content.append(job_description)
                document_content.append(f"```")
            else:
                document_content.append(f"• {job_description}")
            document_content.append("")
            
            # Application Link
            if application.get('link'):
                document_content.append("### Application Link")
                document_content.append(f"• Job Posting URL: {application['link']}")
                document_content.append("")
            
            # Contacted Employees (Referrals)
            if application.get('contactedEmployees'):
                document_content.append("### Contacted Employees (Referrals)")
                for employee in application['contactedEmployees']:
                    document_content.append(f"• **{employee['name']}**")
                    document_content.append(f"  - Job Title: {employee['jobTitle']}")
                    document_content.append(f"  - Email: {employee['email']}")
                    document_content.append(f"  - LinkedIn: {employee['linkedinLink']}")
                    document_content.append(f"  - Contact Status: {employee['contacted']}")
                    document_content.append(f"  - Contacted Date: {employee['createdAt'][:10]}")
                    document_content.append("")
            else:
                document_content.append("### Contacted Employees (Referrals)")
                document_content.append("• No employees contacted for referrals")
                document_content.append("")
            
            # Questions and Answers for this application
            if app_id in questions_by_app_id:
                document_content.append("### Interview/Application Questions & Answers")
                questions = questions_by_app_id[app_id]
                for j, qa in enumerate(questions, 1):
                    document_content.append(f"**Question {j}:** {qa['question1']}")
                    document_content.append(f"**Answer:** {qa['answer']}")
                    document_content.append(f"*Asked on: {qa['createdAt'][:10]}*")
                    document_content.append("")
            else:
                document_content.append("### Interview/Application Questions & Answers")
                document_content.append("• No questions recorded for this application")
                document_content.append("")
            
            # Application Timeline
            document_content.append("### Timeline")
            document_content.append(f"• Application Created: {application['createdAt'][:10]}")
            document_content.append(f"• Last Updated: {application['updatedAt'][:10]}")
            document_content.append(f"• Submission Date: {application['submissionDate']}")
            document_content.append("")
            
            # Separator between applications
            document_content.append("-" * 3)
            document_content.append("")
        
        # Add footer with metadata
        document_content.append("## Document Metadata")
        document_content.append(f"• Total Applications Processed: {total_applications}")
        document_content.append(f"• Document Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        document_content.append(f"• Applications Data Pages: {applications_data.get('totalPages', 1)}")
        document_content.append(f"• Questions Data Total: {questions_data.get('totalCount', 0)}")
        
        # Write to file
        with open(self.document_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(document_content))
        
        print(f"Document successfully generated: {self.document_path}")
        print(f"Processed {total_applications} applications with {questions_data.get('totalCount', 0)} questions")

    async def upload_document_to_r2r(self):
        """
        Upload a document to R2R for RAG processing and update the document_id attribute.
        
        Returns:
            Document ID if successful, None if failed
        """
        if self.client is None:
            print("Cannot upload document: R2R client not available")
            return None
        
        try:
            # Check if file exists
            if not os.path.exists(self.document_path):
                print(f"Error: File {self.document_path} does not exist")
                return None
            
            # Upload document using R2R async client
            print(f"Uploading document: {self.document_path}")
            response = await self.client.documents.create(
                file_path=self.document_path,
                metadata={
                    "source": "job_applications_portfolio",
                    "document_type": "job_applications",
                    "generated_at": datetime.now().isoformat()
                }
            )
            
            print(f"Document uploaded successfully!")
            print(f"Message: {response.results.message}")
            print(f"Task ID: {response.results.task_id}")
            print(f"Document ID: {response.results.document_id}")
            
            # Update the class attribute (convert UUID to string)
            self.document_id = str(response.results.document_id)
            
            return self.document_id
            
        except Exception as e:
            print(f"Error uploading document to R2R: {e}")
            if "already exists" in str(e):
                # Extract document ID from error message
                error_str = str(e)
                if "Document" in error_str and "already exists" in error_str:
                    # Find the UUID pattern in the error message
                    uuid_pattern = r'Document ([a-f0-9-]+) already exists'
                    match = re.search(uuid_pattern, error_str)
                    if match:
                        self.document_id = match.group(1)
                    else:
                        print("Could not extract document ID from error message")
                        return None
                else:
                    print("Unexpected error format")
                    return None
                print(f"Returning existing document ID: {self.document_id}")
                return self.document_id
            return None

    async def check_document_status(self, document_id=None):
        """
        Check the ingestion status of a document in R2R.
        
        Args:
            document_id: ID of the document to check (uses self.document_id if not provided)
        """
        if self.client is None:
            print("R2R client not available")
            return None
        
        doc_id = document_id or self.document_id
        if not doc_id:
            print("No document ID available")
            return None
        
        try:
            documents_response = await self.client.documents.list()
            # Handle the response structure properly
            documents = documents_response.results if hasattr(documents_response, 'results') else documents_response
            
            for doc in documents:
                if str(doc.id) == str(doc_id):
                    print(f"Document Status:")
                    print(f"  ID: {doc.id}")
                    print(f"  Ingestion Status: {doc.ingestion_status}")
                    if hasattr(doc, 'size_in_bytes'):
                        print(f"  Size: {doc.size_in_bytes} bytes")
                    if hasattr(doc, 'created_at'):
                        print(f"  Created: {doc.created_at}")
                    return doc
            print(f"Document with ID {doc_id} not found")
            return None
        except Exception as e:
            print(f"Error checking document status: {e}")
            return None

    async def delete_document(self, document_id=None):
        """
        Delete a document from R2R.
        
        Args:
            document_id: ID of the document to delete (uses self.document_id if not provided)
        """
        print(f"Deleting document: {document_id}")
        
        # Delete the local document file if it exists
        if self.document_path and os.path.exists(self.document_path):
            try:
                os.remove(self.document_path)
                print(f"Local document file deleted: {self.document_path}")
            except Exception as e:
                print(f"Error deleting local document file: {e}")
        if self.client is None:
            print("R2R client not available")
            return None
        
        doc_id = document_id or self.document_id
        if not doc_id:
            print("No document ID available")
            return None
        
        try:
            response = await self.client.documents.delete(doc_id)
            print(f"Document deleted successfully: {response}")
            
            # Clear the document_id if we deleted the current document
            if doc_id == self.document_id:
                self.document_id = None
                
            return response
        except Exception as e:
            print(f"Error deleting document: {e}")
            return None

    async def send_message_to_r2r(self, message, document_id=None, conversation_id=None):
        """
        Send a message to R2R using agent mode.
        
        Args:
            message: Message to send
            document_id: Document ID to filter search (uses self.document_id if not provided)
            conversation_id: Conversation ID (uses self.conversation_id if not provided, creates new if None)
        
        Returns:
            Response content as string
        """
        if self.client is None:
            print("R2R client not available")
            return None
        
        doc_id = document_id or self.document_id
        if not doc_id:
            print("No document ID available")
            return None
        
        conv_id = conversation_id or self.conversation_id
        
        try:
            if conv_id is None:
                # Create a new conversation and update the class attribute
                conversation = await self.client.conversations.create()
                print(f"Conversation created: {conversation.results.id}")
                self.conversation_id = str(conversation.results.id)
                conv_id = self.conversation_id
            
            query = """### Answer the following query without any additional context or mentioning the document in your response:
            """
            response = await self.client.retrieval.agent(
                message={"role": "user", "content": query + message},
                search_settings={
                "limit": 25,
                "filter": {
                    "document_id": doc_id
                }
                },
                rag_generation_config={
                    "model": "gpt-4o-mini",  # Use a more reliable model
                    "temperature": 0.1,
                    "max_tokens_to_sample": 4000,
                    "stream": False
                },
                conversation_id=conv_id,
                mode="rag"
            )
            return response.results.messages[-1].content
        except Exception as e:
            print(f"Error sending message to R2R: {e}")
            return None

    async def send_query_to_r2r(self, message, document_id=None):
        """
        Send a query to R2R using RAG mode.
        
        Args:
            message: Message to send
            document_id: Document ID to filter search (uses self.document_id if not provided)
        
        Returns:
            Response content as string
        """
        if self.client is None:
            print("R2R client not available")
            return None
        
        doc_id = document_id or self.document_id
        if not doc_id:
            print("No document ID available")
            return None
        
        query = """### Answer the following query without any additional context or mentioning the document in your response:
        """
        try:
            response = await self.client.retrieval.rag(
            query=query + message,
            search_settings={
                "limit": 25,
                "filter": {
                    "document_id": doc_id
                }
            },
            rag_generation_config={
                "model": "gpt-4o-mini",  # Use a more reliable model
                "temperature": 0.1,
                "max_tokens_to_sample": 4000,
                "stream": False
            }
        )
            print(f"Message sent successfully: {response.results.completion}")
            return response.results.completion
        except Exception as e:  
            print(f"Error sending message to R2R: {e}")
            return None


async def main():
    """
    Main async function to demonstrate R2RChatbot usage.
    """
    try:
        # Initialize the chatbot
        chatbot = R2RChatbot(user_id=4)
        
        if chatbot.client is None:
            print("R2R client not available. Please check your API key or run a local R2R instance.")
            return
        
        # Load applications data
        with open('applications.json', 'r', encoding='utf-8') as f:
            applications_data = json.load(f)
        
        # Load questions data
        with open('questions.json', 'r', encoding='utf-8') as f:
            questions_data = json.load(f)
        
        # Generate the document
        chatbot.generate_application_document(applications_data, questions_data)
        
        # Upload to R2R
        print("\nUploading to R2R...")
        document_id = await chatbot.upload_document_to_r2r()
        if document_id:
            print(f"Successfully uploaded to R2R with ID: {document_id}")
            # Check status
            print("\nChecking document status...")
            await chatbot.check_document_status()
        
            # Send messages
            response = await chatbot.send_message_to_r2r("how many times did I apply for algoriza?")
            print(response)
            response = await chatbot.send_message_to_r2r("and which one of them was I accepted? what was the date?")
            print(response)
        
    except FileNotFoundError as e:
        print(f"Error: Could not find required JSON file - {e}")
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON format - {e}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
