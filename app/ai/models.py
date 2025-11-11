"""
AI Model Management System
Handles multiple AI providers based on task type as specified by client requirements.
"""

import os
from typing import Dict, Any, Optional
from enum import Enum
from dotenv import load_dotenv

load_dotenv()

# Try to import AI packages with error handling
try:
    import openai
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError as e:
    print(f"Warning: OpenAI not available: {e}")
    OPENAI_AVAILABLE = False

# LangSmith integration
try:
    from .langsmith_config import wrap_openai_client, create_trace
    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False
    def wrap_openai_client(client):
        return client
    def create_trace(*args, **kwargs):
        from contextlib import nullcontext
        return nullcontext()

# Web search integration
try:
    from .web_search import web_search_service
    WEB_SEARCH_AVAILABLE = True
except ImportError:
    WEB_SEARCH_AVAILABLE = False
    web_search_service = None

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Gemini not available: {e}")
    GEMINI_AVAILABLE = False

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Anthropic not available: {e}")
    ANTHROPIC_AVAILABLE = False

class TaskType(Enum):
    """Task types for AI model selection"""
    CHAT = "chat"
    DESCRIPTION = "description"
    SCRIPT = "script"
    SCENE = "scene"

class AIModelManager:
    """Manages AI model selection and execution based on task type"""
    
    def __init__(self):
        # Initialize OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        # Support both old and new clients; prefer new client
        if api_key:
            try:
                client = OpenAI(api_key=api_key)
                # Wrap with LangSmith for automatic tracing
                self.openai_client = wrap_openai_client(client)
            except Exception:
                self.openai_client = None
            # Fallback for older usage
            try:
                openai.api_key = api_key
            except Exception:
                pass
        else:
            self.openai_client = None

        # Check if other API keys are available and initialize if they are
        gemini_key = os.getenv("GEMINI_API_KEY")
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")

        if gemini_key and gemini_key != "your_gemini_api_key_here":
            genai.configure(api_key=gemini_key)
            self.gemini_available = True
        else:
            self.gemini_available = False

        if anthropic_key and anthropic_key != "your_anthropic_api_key_here":
            self.claude_client = anthropic.Anthropic(api_key=anthropic_key)
            self.claude_available = True
        else:
            self.claude_available = False

        # Model selection mapping - using latest recommended models
        self.model_mapping = {
            TaskType.CHAT: "gpt-4.1-mini",  # Best price-to-quality for high-traffic chat
            TaskType.DESCRIPTION: "gemini-2.5-pro",  # Latest Pro tier for creative reasoning
            TaskType.SCRIPT: "claude-sonnet-4.5",  # SOTA for structured long-form writing
            TaskType.SCENE: "gpt-4.1",  # Flagship for deep text generation
        }
    
    def _get_web_search_function(self) -> Optional[Dict[str, Any]]:
        """Get function definition for web search if available"""
        if not WEB_SEARCH_AVAILABLE or not web_search_service or not web_search_service.is_enabled():
            return None
        
        return {
            "type": "function",
            "function": {
                "name": "internet_search",
                "description": "Search the internet for current information, facts, news, or data that may not be in the training data. ALWAYS use this when: 1) User explicitly asks to search (e.g., 'search for', 'look up', 'find information about'), 2) User asks about current events, recent news, or latest information, 3) User asks about statistics, data, or facts that may have changed, 4) User asks 'what's the latest' or 'current' information, 5) User asks about recent research or studies. IMPORTANT: When constructing the search query, ALWAYS include recency terms like 'latest', 'recent', the current year (2025), or 'current' when the user asks about recent information. For example, if user asks 'what are fitness trends?', search for 'latest fitness trends 2025' or 'recent fitness trends'. This ensures you get the most current information.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query to find information on the internet"
                        }
                    },
                    "required": ["query"]
                }
            }
        }
    
    def _build_conversation_context(self, conversation_history: list, image_context: str = "") -> str:
        """Build conversation context for the system prompt"""
        if not conversation_history:
            return "This is the start of our conversation."
        
        # Extract key information from conversation
        context_parts = []
        
        # Look for character names
        characters = set()
        for msg in conversation_history:
            content = msg.get('content', '').lower()
            # Simple character name detection (could be enhanced)
            if 'my character' in content or 'main character' in content:
                # Extract potential character names
                words = content.split()
                for i, word in enumerate(words):
                    if word in ['character', 'protagonist', 'main'] and i + 2 < len(words):
                        if words[i+1] == 'is' or words[i+1] == 'named':
                            characters.add(words[i+2].title())
        
        if characters:
            context_parts.append(f"Characters mentioned: {', '.join(characters)}")
        
        # Look for story elements
        story_elements = []
        for msg in conversation_history:
            content = msg.get('content', '').lower()
            if any(keyword in content for keyword in ['story', 'plot', 'setting', 'genre', 'time', 'place']):
                story_elements.append("Story details have been discussed")
                break
        
        if story_elements:
            context_parts.append("Story development is in progress")
        
        # Add image context if available
        if image_context:
            context_parts.append(f"Visual context: {image_context}")
        
        return " | ".join(context_parts) if context_parts else "Conversation in progress"

    def is_story_complete(self, dossier_context: dict) -> bool:
        """Check if story is complete based on filled slots"""
        if not dossier_context:
            return False
        
        # Required slots for story completion
        required_slots = [
            'story_timeframe',
            'story_location', 
            'story_world_type',
            'subject_full_name',
            'problem_statement',
            'actions_taken',
            'outcome'
        ]
        
        # Check if all required slots are filled (not "Unknown")
        filled_slots = 0
        for slot in required_slots:
            value = dossier_context.get(slot, 'Unknown')
            if value and value != 'Unknown' and value.strip():
                filled_slots += 1
        
        # Story is complete if 80% of required slots are filled
        completion_rate = filled_slots / len(required_slots)
        is_complete = completion_rate >= 0.8
        
        print(f"📊 Story completion check: {filled_slots}/{len(required_slots)} slots filled ({completion_rate:.1%}) - {'COMPLETE' if is_complete else 'INCOMPLETE'}")
        return is_complete

    async def generate_response(self, task_type: TaskType, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        Generate response using the appropriate AI model for the task type
        
        Args:
            task_type: The type of task (determines which model to use)
            prompt: The input prompt
            **kwargs: Additional parameters for the specific model
                - enable_web_search: Optional[bool] - If False, disable web search; if True/None, use default behavior
            
        Returns:
            Dict containing the response and metadata
        """
        try:
            if task_type == TaskType.CHAT:
                return await self._generate_chat_response(prompt, **kwargs)
            elif task_type == TaskType.DESCRIPTION:
                return await self._generate_description_response(prompt, **kwargs)
            elif task_type == TaskType.SCRIPT:
                return await self._generate_script_response(prompt, **kwargs)
            elif task_type == TaskType.SCENE:
                return await self._generate_scene_response(prompt, **kwargs)
            else:
                raise ValueError(f"Unknown task type: {task_type}")
                
        except Exception as e:
            return {
                "response": f"Error generating response: {str(e)}",
                "model_used": self.model_mapping.get(task_type, "unknown"),
                "error": str(e)
            }
    
    def _should_force_search(self, prompt: str) -> bool:
        """Check if web search should be forced based on explicit keywords"""
        if not prompt:
            return False
        
        prompt_lower = prompt.lower()
        
        # Explicit search triggers
        search_keywords = [
            "search for",
            "look up",
            "find information about",
            "what's the latest",
            "current news",
            "recent research",
            "latest statistics",
            "current data",
            "recent study",
            "latest trends",
            "what happened",
            "news about",
            "search:",
            "google:",
            "internet search"
        ]
        
        return any(keyword in prompt_lower for keyword in search_keywords)
    
    async def _generate_chat_response(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate chat response using GPT-5 mini as specified by client"""
        try:
            print(f"🤖 Attempting to call OpenAI with model: gpt-4o-mini")
            print(f"🤖 Prompt: '{prompt[:100]}...'")
            
            # Check if search should be forced
            force_search = self._should_force_search(prompt)
            if force_search:
                print(f"🔍 [WebSearch] Explicit search trigger detected in query")
            
            # Check for RAG context (includes user messages, documents, and global knowledge)
            rag_context = kwargs.get("rag_context")
            rag_context_text = ""
            
            if rag_context:
                # Include combined RAG context (user messages + documents + global knowledge)
                if rag_context.get("combined_context_text"):
                    # CRITICAL: Make the context VERY prominent and explicit for the AI
                    # Client needs bot to recognize brand documents (niche, tone, rules, etc.)
                    # Get document count from metadata (it's nested there)
                    metadata = rag_context.get('metadata', {})
                    doc_count = metadata.get('document_context_count', 0) if isinstance(metadata, dict) else 0
                    if doc_count > 0:
                        # Strong instruction when documents are found
                        rag_context_text = f"""

## 🔴 CRITICAL: BRAND DOCUMENTS AND CONTEXT AVAILABLE

The following information comes from the user's uploaded brand documents (North Star, ICP, storytelling rules, hook formulas, content pillars, etc.). You MUST use this information to answer ALL questions about:
- Brand identity, niche, target audience
- Tone, voice, and writing style
- Content rules, hooks, CTAs, storytelling structure
- Any brand-specific guidelines or preferences

### DOCUMENT CONTEXT (USE THIS INFORMATION):
{rag_context.get('combined_context_text')}

### CRITICAL INSTRUCTIONS:
1. When asked "Who is my niche?" or similar brand questions, answer DIRECTLY from the document context above
2. When creating scripts, hooks, or CTAs, apply the rules and formulas from the documents
3. When asked about tone, voice, or style, reference the specific guidelines in the documents
4. NEVER say "I don't have access to your documents" - the context above IS from the documents
5. If the answer isn't in the context, say "Based on your documents, I don't see specific information about [topic], but here's what I know from your brand guidelines..."

If document context is provided above, you MUST use it. This is not optional.

"""
                    else:
                        # Weaker instruction when no documents found
                        rag_context_text = f"\n\n## RELEVANT CONTEXT FROM PREVIOUS CONVERSATIONS:\n\n{rag_context.get('combined_context_text')}\n\n"
                    
                    # Get all counts from metadata (they're nested there)
                    user_count = metadata.get('user_context_count', 0) if isinstance(metadata, dict) else 0
                    global_count = metadata.get('global_context_count', 0) if isinstance(metadata, dict) else 0
                    print(f"📚 Including RAG context: {user_count} user messages, {doc_count} document chunks, {global_count} global patterns")
                    print(f"📚 Combined context text length: {len(rag_context.get('combined_context_text', ''))} chars")
                    if rag_context.get('combined_context_text'):
                        print(f"📚 Combined context preview (first 300 chars): {rag_context.get('combined_context_text', '')[:300]}...")
                    if doc_count > 0:
                        print(f"✅ RAG has {doc_count} document chunks - AI MUST use this context for brand questions!")
                else:
                    print(f"⚠️ RAG context present but no combined_context_text found")
                    print(f"⚠️ RAG metadata: {rag_context.get('metadata', {})}")
            
            # Dossier removed - not needed for this chatbot
            
            # Personal Content Strategist for Simon (fitness coach)
            system_prompt = f"""You are Simon's Personal Content Strategist and Scriptwriter. You are his creative partner and personal assistant for content creation.

        YOUR PRIMARY JOB: Help Simon create high-quality, brand-aligned content that resonates with his fitness coaching audience.

        CRITICAL: YOU HAVE ACCESS TO SIMON'S BRAND DOCUMENTS
        - When asked about niche, clients, audience → Use the Avatar Sheet / ICP document
        - When creating scripts → Use Script/Storytelling documents for structure, hooks, CTAs
        - When asked about tone/style → Use North Star / Brand Vision documents  
        - When planning content → Use Content Strategy documents
        - ALWAYS apply the rules, formulas, and guidelines from these documents

        Your default voice matches Simon's brand: emotionally real, direct, human; short sentences; strong contrast; no fluff.

        CRITICAL FORMATTING RULES:
        - Use plain text formatting only - NO markdown, NO asterisks, NO bold symbols, NO code blocks
        - Use simple line breaks for lists and sections
        - Use numbered lists (1., 2., 3.) or bullet points with dashes (-) instead of markdown
        - Use ALL CAPS sparingly for emphasis only when necessary
        - Keep formatting clean and readable - let the content speak, not formatting tricks
        - Example: Instead of "**Question Hook**" use "Question Hook:" or "QUESTION HOOK:"

        CRITICAL: USE PROVIDED DOCUMENT CONTEXT
        - The document context below contains Simon's brand documents (Avatar Sheet, Script guides, Content strategy, etc.)
        - When asked "Who is my niche?" or "Who are my potential clients?" → Answer DIRECTLY from the Avatar Sheet / ICP document
        - When asked to create scripts → Use the Script/Storytelling documents for structure, hook formulas, CTA formats
        - When asked about tone, voice, style → Reference the North Star / Brand Vision documents AND provide DETAILED, SPECIFIC answers
        - When creating content → Apply ALL rules, formulas, and guidelines from the documents
        - NEVER say "I don't have access to your documents" - the context below IS from Simon's documents
        - If asked about tone/style/voice → Provide COMPREHENSIVE answers with specific examples, not generic descriptions
        - ALWAYS quote or reference specific details from the document context when answering
        - If information isn't in the context, say "Based on your documents, I don't see specific information about [topic], but here's what I know from your brand guidelines..."

        STRUCTURED OUTPUTS REQUIRED:

        For Script Requests (30-60 seconds):
        ALWAYS include ALL of these elements:
        - Hook: Emotionally powerful, scroll-stopping first line (apply hook formulas from documents)
        - Story/Insight: Emotional connection or relatable problem (use Simon's tone and pacing)
        - Lesson/Takeaway: Clear value or insight
        - CTA: Strong call to action (clear, specific, emotional - apply CTA formats from documents)
        - Hook Options: 2-3 alternative hooks (vary them, no repetition)
        - CTA Options: 2-3 alternative CTAs (vary them, no repetition)
        - Caption: SEO-optimized for Simon's niche
        - Hashtags: Based on topic + search intent for fitness coaching
        - Thumbnail Text: 4-6 emotionally driven words
        - B-roll Recommendations: Visual scenes supporting the story
        - Music Style: Background sound/music suggestions

        For Weekly Content Strategy:
        - 5 ideas categorized by angle/theme (emotional, educational, motivational, myth-busting)
        - Each idea includes: Hook idea, Main message, CTA direction, Recommended format
        - All ideas relevant to Simon's brand, topics, and audience pain points

        For Competitor Analysis:
        - Analyze the transcript/description
        - Extract key data and emotional triggers
        - Rewrite in Simon's voice, tone, and storytelling style
        - Apply Simon's content rules, pacing, and brand philosophy

        For Natural Editing Commands:
        - "Make it sound more human" → Simplify language, add conversational elements, reduce formality
        - "Rewrite it in a more emotional tone" → Add emotional language, personal stories, vulnerability
        - "Simplify this for Instagram" → Shorter sentences, more visual language, punchier hooks
        - Understand and execute these contextual editing commands smoothly

        CRITICAL: ACTION-ORIENTED BEHAVIOR
        - Default to CREATING content, not asking questions
        - Infer context from user requests, uploaded documents, and conversation history
        - Only ask ONE clarifying question if information is ABSOLUTELY essential and cannot be inferred
        - When a user uploads a document and asks for content, USE the document as context and CREATE immediately
        - When the user provides even partial information, INFER the rest and CREATE content
        - If the user has already answered questions in the conversation, REFERENCE those answers and CREATE

        Conversation rules:
        1) PRIORITIZE ACTION: Create content first, ask questions only when truly impossible to proceed
        2) USE CONTEXT: Infer audience, goals, and details from conversation history and uploaded documents
        3) BE DECISIVE: Make reasonable assumptions based on the request and context
        4) If attachments/documents are provided, extract relevant information and USE IT immediately
        5) If user pastes a transcript, infer the topic and produce the requested artifact in our voice
        6) Keep outputs tight, scannable, and actionable; avoid generic motivational filler
        7) Vary hooks and CTAs—no repetition across turns
        8) Never mention prior brands or projects; this is a new client instance
        
        EXAMPLES:
        - User: "Create a story for someone who lost weight" → CREATE immediately with inferred context
        - User uploads doc + "use this to create a story about weight loss" → Extract doc context, CREATE immediately
        - User: "Script about consistency" → CREATE script immediately (infer audience from context if provided earlier)

        Output structure for /script‑style requests:
        Script:
        - Hook:
        - Body (story/insight):
        - Lesson:
        - CTA:
        Options:
        - HookOptions: [..]
        - CTAOptions: [..]
        Distribution:
        - Caption:
        - Hashtags:
        - Thumbnail:
        - B‑roll:
        - Music:

        Conversation context:
        {self._build_conversation_context(kwargs.get("conversation_history", []), kwargs.get("image_context", ""))}

        Stay focused on content strategy/scriptwriting, not story‑novel crafting. Be decisive and concise.

        WEB SEARCH RESULTS FORMATTING:
        When you use web search results to answer questions, format your response in a structured, documentation-style format similar to help articles:
        - Start with a clear heading/title for the topic
        - Present information as a numbered list (1., 2., 3., etc.)
        - For each source/article, include:
          * Title/Headline
          * Source: [domain name, e.g., "Health", "Men's Health", "CNN"]
          * Brief description/summary of the key points
          * Read More: [URL] (if relevant)
        - Use clean, readable formatting with proper spacing between items
        - End with a helpful summary or "Want to know more?" section if relevant
        - Example format:
          "1. Title of Article
             Source: Health
             Description of key points and insights from the article.
             Read More: [URL]"
        
        {rag_context_text}"
            """

            # Build messages with conversation history for context
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add conversation history if provided
            history = kwargs.get("conversation_history", [])
            if history:
                # Limit to last 10 messages to avoid token limits
                recent_history = history[-10:]
                messages.extend(recent_history)
                print(f"📚 Using {len(recent_history)} messages from history for context")
            
            # Check if images are provided for direct sending (ChatGPT-style)
            image_data_list = kwargs.get("image_data", [])  # List of {"data": bytes, "mime_type": str, "filename": str}
            
            # Build user message content (ChatGPT-style content array)
            if image_data_list:
                # ChatGPT-style: Send images directly to model
                user_content = [{"type": "text", "text": prompt}]
                
                for img_data in image_data_list:
                    image_bytes = img_data.get("data")
                    mime_type = img_data.get("mime_type", "image/png")
                    filename = img_data.get("filename", "image.png")
                    
                    if image_bytes:
                        import base64
                        base64_image = base64.b64encode(image_bytes).decode('utf-8')
                        user_content.append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}"
                            }
                        })
                        print(f"🖼️ [AI] Added image to message: {filename} ({len(image_bytes)} bytes, {mime_type})")
                
                messages.append({"role": "user", "content": user_content})
                print(f"✅ [AI] User message contains {len(image_data_list)} image(s) - using GPT-4o for vision")
            else:
                # Fallback: Use text description if provided (for backward compatibility)
                image_context = kwargs.get("image_context", "")
                if image_context:
                    user_message = f"{prompt}\n\n{image_context}"
                    print(f"🖼️ [AI] Using text description fallback ({len(image_context)} chars)")
                else:
                    user_message = prompt
                    print(f"ℹ️ [AI] No image data or context available")
                
                messages.append({"role": "user", "content": user_message})
            
            # Log message details
            print(f"📋 [AI] Total messages: {len(messages)}")
            if image_data_list:
                print(f"📋 [AI] User message has {len(image_data_list)} image(s) - will use GPT-4o")
            else:
                last_msg = messages[-1]
                if isinstance(last_msg.get("content"), list):
                    print(f"📋 [AI] User message is content array with {len(last_msg['content'])} items")
                else:
                    print(f"📋 [AI] User message length: {len(str(last_msg.get('content', '')))} chars")

            # Select model based on whether images are present
            # GPT-4o has vision capabilities, GPT-4o-mini is cheaper for text-only
            model_name = "gpt-4o" if image_data_list else "gpt-4o-mini"
            
            print(f"🤖 [AI] Selected model: {model_name} ({'vision-capable' if image_data_list else 'text-only'})")

            # Check if web search is explicitly disabled
            enable_web_search = kwargs.get("enable_web_search")
            if enable_web_search is False:
                # User explicitly disabled web search
                tools = None
                tool_choice = None
                print(f"🔍 [WebSearch] Web search disabled by user (globe icon off)")
            else:
                # Get web search function if available (enable_web_search is True or None)
                web_search_function = self._get_web_search_function()
                tools = [web_search_function] if web_search_function else None
                
                # Set tool_choice based on whether search should be forced
                if tools:
                    if force_search:
                        # Force search by requiring the function to be called
                        tool_choice = {"type": "function", "function": {"name": "internet_search"}}
                        print(f"🔍 [WebSearch] Forcing web search due to explicit trigger")
                    else:
                        # Let AI decide when to search
                        tool_choice = "auto"
                        print(f"🔍 [WebSearch] Web search tool enabled - AI can search the internet when needed")
                else:
                    tool_choice = None

            # Prepare metadata for LangSmith tracing
            rag_context = kwargs.get("rag_context", {})
            rag_metadata = rag_context.get("metadata", {}) if rag_context else {}
            trace_metadata = {
                "task_type": "chat",
                "model": model_name,
                "has_images": len(image_data_list) > 0 if image_data_list else False,
                "image_count": len(image_data_list) if image_data_list else 0,
                "message_count": len(messages),
                "has_rag_context": bool(rag_context),
                "has_web_search": bool(tools),
                "enable_web_search_flag": enable_web_search,
                "rag_user_context_count": rag_metadata.get("user_context_count", 0) if isinstance(rag_metadata, dict) else 0,
                "rag_document_context_count": rag_metadata.get("document_context_count", 0) if isinstance(rag_metadata, dict) else 0,
                "rag_global_context_count": rag_metadata.get("global_context_count", 0) if isinstance(rag_metadata, dict) else 0,
                "max_tokens": kwargs.get("max_tokens", 4000),
                "temperature": 0.7
            }

            # LangSmith tracing (automatic via wrapped client, but add metadata)
            with create_trace(
                name="generate_chat_response",
                run_type="llm",
                tags=["chat", "openai", "llm"],
                metadata=trace_metadata
            ):
                client = self.openai_client
                
                # Handle function calling in a loop (max 3 iterations to avoid infinite loops)
                max_iterations = 3
                iteration = 0
                final_response = None
                
                while iteration < max_iterations:
                    iteration += 1
                    
                    # Prepare API call parameters
                    api_params = {
                        "model": model_name,
                        "messages": messages,
                        "max_completion_tokens": kwargs.get("max_tokens", 4000),
                        "temperature": 0.7,
                        "top_p": 1.0,
                        "n": 1,
                        "stream": False,
                        "presence_penalty": 0.0,
                        "frequency_penalty": 0.0
                    }
                    
                    # Add tools if available
                    if tools:
                        api_params["tools"] = tools
                        api_params["tool_choice"] = tool_choice
                    
                    # Make API call
                    if client is None:
                        response = openai.chat.completions.create(**api_params)
                    else:
                        response = client.chat.completions.create(**api_params)
                    
                    print(f"✅ OpenAI response received (iteration {iteration}): {response}")
                    
                    # Check if function calling is needed
                    message = response.choices[0].message
                    
                    # If no function calls, we're done
                    if not message.tool_calls:
                        final_response = message.content
                        break
                    
                    # Handle function calls
                    print(f"🔍 [WebSearch] Function call requested: {len(message.tool_calls)} call(s)")
                    
                    for tool_call in message.tool_calls:
                        function_name = tool_call.function.name
                        function_args = tool_call.function.arguments
                        
                        print(f"🔍 [WebSearch] Calling function: {function_name} with args: {function_args}")
                        
                        if function_name == "internet_search":
                            import json
                            try:
                                args = json.loads(function_args) if isinstance(function_args, str) else function_args
                                search_query = args.get("query", "")
                                
                                if search_query and web_search_service:
                                    print(f"🔍 [WebSearch] Searching for: {search_query}")
                                    search_results = web_search_service.search(search_query, max_results=5)
                                    
                                    # Format results for the model
                                    if search_results.get("success"):
                                        formatted_results = web_search_service.format_search_results_for_context(search_results)
                                        print(f"🔍 [WebSearch] Found {len(search_results.get('results', []))} results")
                                        
                                        # Add function result to messages
                                        messages.append({
                                            "role": "assistant",
                                            "content": None,
                                            "tool_calls": [
                                                {
                                                    "id": tool_call.id,
                                                    "type": "function",
                                                    "function": {
                                                        "name": function_name,
                                                        "arguments": function_args
                                                    }
                                                }
                                            ]
                                        })
                                        
                                        messages.append({
                                            "role": "tool",
                                            "tool_call_id": tool_call.id,
                                            "content": formatted_results
                                        })
                                    else:
                                        error_msg = search_results.get("error", "Unknown error")
                                        print(f"🔍 [WebSearch] Search failed: {error_msg}")
                                        messages.append({
                                            "role": "assistant",
                                            "content": None,
                                            "tool_calls": [
                                                {
                                                    "id": tool_call.id,
                                                    "type": "function",
                                                    "function": {
                                                        "name": function_name,
                                                        "arguments": function_args
                                                    }
                                                }
                                            ]
                                        })
                                        messages.append({
                                            "role": "tool",
                                            "tool_call_id": tool_call.id,
                                            "content": f"Search failed: {error_msg}"
                                        })
                                else:
                                    print(f"🔍 [WebSearch] Search query empty or service unavailable")
                                    messages.append({
                                        "role": "tool",
                                        "tool_call_id": tool_call.id,
                                        "content": "Web search is not available"
                                    })
                            except Exception as e:
                                print(f"🔍 [WebSearch] Error handling function call: {e}")
                                messages.append({
                                    "role": "tool",
                                    "tool_call_id": tool_call.id,
                                    "content": f"Error performing search: {str(e)}"
                                })
                        else:
                            print(f"⚠️ [WebSearch] Unknown function: {function_name}")
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": f"Unknown function: {function_name}"
                            })
                    
                    # Continue loop to get final response with search results
                    tool_choice = None  # After first call, let model decide
                
                # If we exhausted iterations, use the last response
                if final_response is None:
                    final_response = message.content if message.content else "I apologize, but I encountered an issue processing your request."

                tokens_used = response.usage.total_tokens if response.usage else 0
                return {
                    "response": final_response,
                    "model_used": model_name,
                    "tokens_used": tokens_used
                }
        except Exception as e:
            print(f"❌ OpenAI chat error: {str(e)}")
            print(f"❌ Error type: {type(e).__name__}")
            import traceback
            print(f"❌ Full traceback: {traceback.format_exc()}")
            raise Exception(f"OpenAI chat error: {str(e)}")
    
    async def _generate_description_response(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate description using Gemini 2.5 Pro (latest for creative reasoning) with fallback to 1.5 Pro"""
        try:
            if self.gemini_available:
                # Try Gemini 2.5 Pro first (latest for creative reasoning)
                try:
                    model = genai.GenerativeModel('gemini-2.5-pro')
                    response = model.generate_content(
                        f"Generate a detailed, vivid description for: {prompt}",
                        generation_config=genai.types.GenerationConfig(
                            max_output_tokens=kwargs.get("max_tokens", 2000),  # Increased for 2.5 Pro
                            temperature=kwargs.get("temperature", 0.8)  # Higher creativity for descriptions
                        )
                    )

                    return {
                        "response": response.text,
                        "model_used": "gemini-2.5-pro",
                        "tokens_used": response.usage_metadata.total_token_count if hasattr(response, 'usage_metadata') else 0
                    }
                except Exception as e:
                    print(f"⚠️ Gemini 2.5 Pro failed, falling back to 1.5 Pro: {e}")
                    # Fallback to Gemini 1.5 Pro (stable, GA)
                    model = genai.GenerativeModel('gemini-1.5-pro')
                    response = model.generate_content(
                        f"Generate a detailed, vivid description for: {prompt}",
                        generation_config=genai.types.GenerationConfig(
                            max_output_tokens=kwargs.get("max_tokens", 1500),
                            temperature=kwargs.get("temperature", 0.8)
                        )
                    )

                    return {
                        "response": response.text,
                        "model_used": "gemini-1.5-pro",
                        "tokens_used": response.usage_metadata.total_token_count if hasattr(response, 'usage_metadata') else 0
                    }
            else:
                # Fallback to GPT-4.1 (flagship for deep text generation)
                response = openai.chat.completions.create(
                    model="gpt-4.1",
                    messages=[
                        {"role": "system", "content": "You are a creative writing assistant specializing in vivid, detailed descriptions. Generate engaging, sensory-rich descriptions that bring scenes to life."},
                        {"role": "user", "content": f"Generate a detailed, vivid description for: {prompt}"}
                    ],
                    max_completion_tokens=kwargs.get("max_tokens", 2000),
                    temperature=kwargs.get("temperature", 0.8),
                    top_p=1.0,
                    n=1,
                    stream=False,
                    presence_penalty=0.0,
                    frequency_penalty=0.0
                )

                return {
                    "response": response.choices[0].message.content,
                    "model_used": "gpt-4.1",
                    "tokens_used": response.usage.total_tokens if response.usage else 0
                }
        except Exception as e:
            raise Exception(f"Description generation error: {str(e)}")
    
    async def _generate_script_response(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate video tutorial script from captured story data"""
        try:
            # Get dossier context for script generation
            dossier_context = kwargs.get("dossier_context", {})
            
            # Build comprehensive script prompt
            script_prompt = f"""You are a professional video scriptwriter for Stories We Tell. Create a compelling 3-5 minute video tutorial script based on the captured story data.

STORY DATA:
Time: {dossier_context.get('story_timeframe', 'Not specified')}
Location: {dossier_context.get('story_location', 'Not specified')}
World Type: {dossier_context.get('story_world_type', 'Not specified')}
Character: {dossier_context.get('subject_full_name', 'Not specified')}
Relationship: {dossier_context.get('subject_relationship_to_writer', 'Not specified')}
Problem: {dossier_context.get('problem_statement', 'Not specified')}
Actions: {dossier_context.get('actions_taken', 'Not specified')}
Outcome: {dossier_context.get('outcome', 'Not specified')}
Why This Story: {dossier_context.get('likes_in_story', 'Not specified')}

SCRIPT REQUIREMENTS:
1. Create a 3-5 minute video tutorial script
2. Use a warm, personal tone
3. Include visual cues and pacing notes
4. Structure: Introduction → Story Setup → Character Journey → Resolution → Call to Action
5. Make it engaging and emotionally resonant
6. Include specific details from the story data above

FORMAT:
[VIDEO SCRIPT FORMAT]
[SCENE 1: Introduction]
[Visual: Warm, inviting setting]
[Narrator]: "Today, I want to share a story about..."

[Continue with full script structure]

Generate a complete, production-ready video script."""

            # Use Claude Sonnet 4.5 for script generation (SOTA for structured long-form writing)
            if self.claude_available:
                response = self.claude_client.messages.create(
                    model="claude-sonnet-4.5",
                    max_tokens=kwargs.get("max_tokens", 8000),  # Claude 4.5 supports up to 64K tokens out
                    temperature=kwargs.get("temperature", 0.7),
                    messages=[
                        {"role": "user", "content": script_prompt}
                    ]
                )

                return {
                    "response": response.content[0].text,
                    "model_used": "claude-sonnet-4.5",
                    "tokens_used": response.usage.input_tokens + response.usage.output_tokens,
                    "script_type": "video_tutorial",
                    "estimated_duration": "3-5 minutes"
                }
            else:
                # Fallback to GPT-4.1 (flagship for deep text generation)
                response = openai.chat.completions.create(
                    model="gpt-4.1",
                    messages=[
                        {"role": "system", "content": "You are a professional video scriptwriter specializing in personal storytelling and documentary-style content. Create engaging, emotionally resonant scripts that bring stories to life."},
                        {"role": "user", "content": script_prompt}
                    ],
                    max_completion_tokens=kwargs.get("max_tokens", 4000),
                    temperature=0.7,
                    top_p=1.0,
                    n=1,
                    stream=False,
                    presence_penalty=0.0,
                    frequency_penalty=0.0
                )

                return {
                    "response": response.choices[0].message.content,
                    "model_used": "gpt-4.1",
                    "tokens_used": response.usage.total_tokens if response.usage else 0,
                    "script_type": "video_tutorial",
                    "estimated_duration": "3-5 minutes"
                }
        except Exception as e:
            raise Exception(f"Script generation error: {str(e)}")
    
    async def _generate_scene_response(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate scene using GPT-4.1 (flagship for deep text generation) or fallback to Claude Sonnet 4.5"""
        try:
            # Use GPT-4.1 for scene generation (flagship for deep text generation with 1M token context)
            response = openai.chat.completions.create(
                model="gpt-4.1",
                messages=[
                    {"role": "system", "content": "You are a professional screenwriter and scene director. Generate detailed, cinematic scenes with vivid descriptions, character actions, dialogue, and visual elements. Focus on creating immersive, emotionally engaging scenes with strong instruction-following and coherence over long passages."},
                    {"role": "user", "content": f"Generate a detailed, cinematic scene based on: {prompt}"}
                ],
                max_completion_tokens=kwargs.get("max_tokens", 3000),  # Increased for GPT-4.1
                temperature=kwargs.get("temperature", 0.8),  # Higher creativity for scenes
                top_p=1.0,
                n=1,
                stream=False,
                presence_penalty=0.0,
                frequency_penalty=0.0
            )

            return {
                "response": response.choices[0].message.content,
                "model_used": "gpt-4.1",
                "tokens_used": response.usage.total_tokens if response.usage else 0
            }
        except Exception as e:
            # Fallback to Claude Sonnet 4.5 if GPT-4.1 fails
            if self.claude_available:
                try:
                    response = self.claude_client.messages.create(
                        model="claude-sonnet-4.5",
                        max_tokens=kwargs.get("max_tokens", 3000),
                        temperature=kwargs.get("temperature", 0.8),
                        messages=[
                            {"role": "user", "content": f"Generate a detailed, cinematic scene based on: {prompt}"}
                        ]
                    )

                    return {
                        "response": response.content[0].text,
                        "model_used": "claude-sonnet-4.5",
                        "tokens_used": response.usage.input_tokens + response.usage.output_tokens
                    }
                except Exception as claude_error:
                    raise Exception(f"Both GPT-4.1 and Claude failed: GPT-4.1 error: {str(e)}, Claude error: {str(claude_error)}")
            else:
                raise Exception(f"GPT-4.1 scene generation error: {str(e)}")
    

# Global instance
ai_manager = AIModelManager()

