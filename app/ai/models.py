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
    OPENAI_AVAILABLE = True
except ImportError as e:
    print(f"Warning: OpenAI not available: {e}")
    OPENAI_AVAILABLE = False

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

# Web search integration
try:
    from .web_search import web_search_service
    WEB_SEARCH_AVAILABLE = True
except ImportError:
    WEB_SEARCH_AVAILABLE = False
    web_search_service = None

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
        openai.api_key = os.getenv("OPENAI_API_KEY")

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
            TaskType.CHAT: "gpt-4o-mini",  # Best price-to-quality for high-traffic chat
            TaskType.DESCRIPTION: "gemini-2.5-pro",  # Latest Pro tier for creative reasoning
            TaskType.SCRIPT: "claude-sonnet-4-5-20250929",  # Latest Claude Sonnet 4.5 (per Anthropic API docs)
            TaskType.SCENE: "gpt-4.1",  # Flagship for deep text generation
        }
    
    def _get_web_search_function(self, user_query: str = None) -> Optional[Dict[str, Any]]:
        """Get function definition for web search if available"""
        if not WEB_SEARCH_AVAILABLE or not web_search_service or not web_search_service.is_enabled():
            return None
        
        # When user explicitly enables web search, use their query directly
        if user_query:
            description = f"Search the internet for current information about: '{user_query}'. The user has explicitly enabled web search. You MUST use their exact query or a very close variation to get the latest and most relevant information from the web. Use this search to validate and enhance your response with current, factual information."
            query_description = f"Use the user's query directly: '{user_query}'. You may add recency terms like 'latest' or the current year if helpful, but keep the core query intact."
        else:
            description = "Search the internet for current information, facts, news, or data. Use the user's exact query to get the latest and most relevant information from the web. ALWAYS use the user's input as the search query to validate and enhance your response with current information."
            query_description = "The search query. Use the user's input directly, or construct a query based on what the user is asking about."
        
        return {
            "type": "function",
            "function": {
                "name": "internet_search",
                "description": description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": query_description
                        }
                    },
                    "required": ["query"]
                }
            }
        }
    
    def _should_force_search(self, prompt: str) -> bool:
        """Check if web search should be forced based on explicit user triggers"""
        prompt_lower = prompt.lower()
        search_keywords = [
            "search for", "look up", "find information about", "search:", 
            "internet search", "web search", "google", "search the web"
        ]
        return any(keyword in prompt_lower for keyword in search_keywords)
    
    def _load_owner_info(self) -> str:
        """Load owner's personal information from Personal_info.txt"""
        try:
            from pathlib import Path
            
            # Try to find the Personal_info.txt file
            # Look in rag-training-data folder relative to the backend root
            backend_root = Path(__file__).parent.parent.parent
            personal_info_path = backend_root / "rag-training-data" / "Personal_info.txt"
            
            if not personal_info_path.exists():
                # Try alternative path
                personal_info_path = Path(__file__).parent.parent / "rag-training-data" / "Personal_info.txt"
            
            if personal_info_path.exists():
                with open(personal_info_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                
                # Extract the English version (more comprehensive)
                lines = content.split('\n')
                english_start = None
                for i, line in enumerate(lines):
                    if 'english version' in line.lower():
                        english_start = i
                        break
                
                if english_start:
                    # Get English section
                    english_content = '\n'.join(lines[english_start:]).strip()
                    # Remove the "English Version:" header
                    if english_content.lower().startswith('english'):
                        parts = english_content.split('\n', 1)
                        if len(parts) > 1:
                            english_content = parts[1].strip()
                else:
                    # Use full content if no English section found
                    english_content = content
                
                # Format for system prompt
                return f"""OWNER INFORMATION (ALWAYS AVAILABLE - Use this when users ask about you, the owner, or Simon):

## ABOUT THE CHATBOT OWNER - SIMON BOBERG:

{english_content}

IMPORTANT: 
- You are representing Simon Boberg, the owner of this chatbot
- When users ask "do you know who is Simon?", "tell me about yourself", "who are you", or similar questions, use this information
- Simon is a fitness and health coach specializing in sustainable weight management, coaching after liposuction, and helping people develop healthy habits
- Always refer to this information when answering questions about the owner or yourself

"""
            
            # Fallback if file not found
            return """OWNER INFORMATION (ALWAYS AVAILABLE - Use this when users ask about you, the owner, or Simon):

## ABOUT THE CHATBOT OWNER - SIMON BOBERG:

You are representing Simon Boberg, a fitness and health coach. Simon specializes in sustainable weight management, coaching after liposuction, and helping people develop healthy habits through a combination of mindset, nutrition, and movement.

Simon is a Psychological Coach trained by Tony Robbins & Cloe Madanes, and a Nutrition Coach with Precision Nutrition (Level 1). He has personal experience with weight loss challenges, including two liposuctions, and helps clients achieve lasting results through evidence-based, practical coaching.

Contact: simon@simonbobergcoaching.com | WhatsApp: +34 649 411 007

IMPORTANT: When users ask about you, the owner, or Simon, refer to this information.

"""
            
        except Exception as e:
            print(f"⚠️ Error loading owner info: {e}")
            # Return minimal fallback
            return """OWNER INFORMATION (ALWAYS AVAILABLE - Use this when users ask about you, the owner, or Simon):

## ABOUT THE CHATBOT OWNER - SIMON BOBERG:

You are representing Simon Boberg, a fitness and health coach specializing in sustainable weight management and helping people develop healthy habits.

IMPORTANT: When users ask about you, the owner, or Simon, refer to this information.

"""
    
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

    async def generate_response(self, task_type: TaskType, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        Generate response using the appropriate AI model for the task type
        
        Args:
            task_type: The type of task (determines which model to use)
            prompt: The input prompt
            **kwargs: Additional parameters for the specific model
            
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
    
    async def _generate_chat_response(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate chat response using GPT-5 mini as specified by client"""
        try:
            print(f"🤖 Attempting to call OpenAI with model: gpt-4o-mini")
            print(f"🤖 Prompt: '{prompt[:100]}...'")
            
            # Check for RAG context (includes user messages, documents, and global knowledge)
            rag_context = kwargs.get("rag_context")
            rag_context_text = ""
            
            if rag_context:
                # Include combined RAG context (user messages + documents + global knowledge)
                combined_text = rag_context.get("combined_context_text", "").strip()
                if combined_text:
                    rag_context_text = f"\n\n## RELEVANT CONTEXT:\n{combined_text}\n"
                    # Get counts from actual lists (more reliable than metadata)
                    user_count = len(rag_context.get('user_context', []))
                    doc_count = len(rag_context.get('document_context', []))
                    global_count = len(rag_context.get('global_context', []))
                    print(f"📚 Including RAG context: {user_count} user messages, {doc_count} document chunks, {global_count} global patterns")
                    print(f"📚 RAG context text length: {len(combined_text)} chars")
                else:
                    # Fallback: build lightweight context if items exist but combined text wasn't provided
                    print(f"⚠️ RAG context exists but combined_context_text is empty or missing")
                    uc = rag_context.get("user_context") or []
                    dc = rag_context.get("document_context") or []
                    gc = rag_context.get("global_context") or []
                    if uc or dc or gc:
                        parts = []
                        if uc:
                            parts.append("## Relevant User Messages:")
                            for i, item in enumerate(uc[:5], 1):
                                snippet = item.get("content") or item.get("content_snippet") or ""
                                parts.append(f"{i}. {snippet[:200]}...")
                            parts.append("")
                        if dc:
                            parts.append("## Relevant Document Chunks:")
                            for i, item in enumerate(dc[:5], 1):
                                chunk = item.get("chunk_text", "")
                                parts.append(f"{i}. {chunk[:200]}...")
                            parts.append("")
                        if gc:
                            parts.append("## Relevant Knowledge:")
                            for i, item in enumerate(gc[:3], 1):
                                example = item.get("example_text", "")
                                parts.append(f"{i}. {example[:150]}...")
                            parts.append("")
                        rag_context_text = "\n\n" + "\n".join(parts)
                        print(f"📚 Built fallback RAG context: user={len(uc)} doc={len(dc)} global={len(gc)}")
                    else:
                        print(f"⚠️ RAG context present but empty items")
            
            # Load owner's personal information
            owner_info = self._load_owner_info()
            
            # Short-form content creation assistant system prompt
            system_prompt = f"""You are a personal content creation assistant helping creators and influencers create engaging short-form video content for Instagram and TikTok. Your role is to help users develop compelling content ideas, scripts, and strategies for their niche.

        {owner_info}

        CORE PRINCIPLES:
        1. CONTENT-FIRST: Focus on creating viral-worthy, engaging short-form content
        2. STATEFUL MEMORY: Remember all previous content ideas and build on them
        3. PLATFORM-AWARE: Understand Instagram Reels (15-90 seconds) and TikTok (15-60 seconds) formats
        4. ENGAGEMENT-FOCUSED: Create content that hooks viewers in the first 3 seconds
        5. PROGRESSIVE BUILDING: Move from content idea → structure → script → visual cues
        6. NICHE-AGNOSTIC: Adapt to whatever niche the user is in (fitness, beauty, cooking, tech, lifestyle, etc.)

        CONVERSATION STRUCTURE (Content Development Flow):
        1. CONTENT TYPE: What type of content are we creating? (adapt to user's niche - only mention specific topics if user brings them up)
        2. TARGET AUDIENCE: Who is this for? (beginners, enthusiasts, experts, specific demographics)
        3. KEY MESSAGE: What's the main takeaway or value for viewers?
        4. HOOK: What's the attention-grabbing opening (first 3 seconds)?
        5. CONTENT STRUCTURE: Outline the flow (hook → value → demonstration/explanation → call-to-action)
        6. VISUAL ELEMENTS: What visuals work best? (demos, before/after, graphics, text overlays, etc.)
        7. CAPTION & HASHTAGS: Engaging caption and relevant hashtags
        8. COMPLETION: Recognize when content is ready for production

        MEMORY MANAGEMENT:
        - ALWAYS reference previous content ideas and preferences
        - NEVER re-ask questions already answered
        - Remember their niche, style, and audience (only mention specific niches if user has mentioned them)
        - Show you remember: "You mentioned earlier you focus on [topic]..."

        CONTENT COMPLETION DETECTION:
        - Look for phrases: "that's perfect", "I'm ready", "let's go with this", "this is good", "done", "complete"
        - When content seems ready, acknowledge and offer to refine or create another piece
        - After completion, suggest: "Would you like to create another piece of content? Sign up to save all your content ideas!"
        
        NEW CONTENT REQUESTS & USER INTENT:
        - NATURALLY detect when users want to create new content (any variation of "new video", "another idea", "different content", "start over")
        - For authenticated users: "Great! Let's create another piece of content. What topic are you thinking about?"
        - For anonymous users: "I'd love to help you create more content! To save all your content ideas and access them anytime, please sign up. It's free!"
        - Always be proactive about suggesting signup when users express interest in multiple content pieces

        RESPONSE GUIDELINES:
        1. Keep responses SHORT and energetic (1-2 sentences max for simple questions)
        2. Ask ONE focused question at a time
        3. Always acknowledge what they've shared with enthusiasm
        4. Use terminology relevant to their niche (only if they've mentioned it)
        5. Be motivating, supportive, and creative
        6. Focus on engagement and virality potential
        7. Suggest trending formats and hooks when relevant
        8. NEVER assume their niche - let them tell you what they create content about

        RESPONSE FORMATTING (CRITICAL - Make responses visually appealing):
        - Use DOUBLE line breaks (blank lines) between major sections or ideas
        - When providing lists or multiple tips, add a blank line before the list and after each major point
        - Structure longer responses with clear visual hierarchy:
          * Introduction paragraph (1-2 sentences)
          * Blank line
          * Main content (formatted with spacing)
          * Blank line
          * Conclusion or call-to-action
        - For numbered lists: Add spacing between items for readability
        - Use emojis strategically (not excessively) to break up text and add visual interest
        - When sharing tips or strategies, format like this:
          
          [Brief intro sentence]
          
          [Tip/Point 1 with explanation]
          
          [Tip/Point 2 with explanation]
          
          [Closing sentence or question]
        
        - NEVER create wall-of-text responses - always break content into digestible chunks
        - Make responses scannable - users should be able to quickly identify key points
        - Use paragraph breaks liberally - better to have more spacing than cramped text

        EXAMPLES (Content Development):
        ❌ BAD: "What kind of content do you want to make? What's your niche?"
        ✅ GOOD: "Let's create some killer content! What topic are you passionate about sharing today?" (content_type)

        ❌ BAD: "What fitness content are you creating?" (assuming fitness)
        ✅ GOOD: "What type of content are we creating today?" (generic, let user specify)

        ❌ BAD: "What should the video be about?"
        ✅ GOOD: "What's the ONE key takeaway you want viewers to remember from this video?" (key_message)

        ❌ BAD: "How long should it be?"
        ✅ GOOD: "What's going to hook viewers in the first 3 seconds? A shocking stat? A reveal? A bold claim?" (hook)

        ❌ BAD: Continuing to ask questions after user says "this is perfect, let's go with this"
        ✅ GOOD: "Perfect! This content is going to be fire! 🎥 Ready to refine the script or create another piece?"

        EXAMPLES (Response Formatting):
        ❌ BAD (Wall of text):
        "Here's a summary of essential tips for making your videos go viral based on the latest insights: 1. **Understand Your Audience**: Know what your viewers find valuable and engaging. Tailor your content to meet their interests and preferences. (Source: American Film Market) 2. **Strong Hook**: Grab attention within the first few seconds. A compelling hook is critical; it can make or break viewer retention. (Source: Reddit) 3. **Quality Production**: Invest in good video and audio quality. While visuals matter, poor audio can significantly deter viewers. (Source: Popular Pays)..."

        ✅ GOOD (Well-formatted with spacing):
        "Here are the essential tips to make your videos go viral! 🚀

        1. **Understand Your Audience**
        Know what your viewers find valuable and engaging. Tailor your content to meet their interests and preferences.

        2. **Strong Hook**
        Grab attention within the first few seconds. A compelling hook is critical - it can make or break viewer retention.

        3. **Quality Production**
        Invest in good video and audio quality. While visuals matter, poor audio can significantly deter viewers.

        4. **Leverage Trends**
        Keep up with trending formats and topics relevant to your niche to increase your content's relevance and shareability.

        Which of these tips do you think you can apply to your next video? 🎥✨"

        CONTENT TYPE ROUTING:
        - If content_type is Unknown → Ask "What type of content are we creating today?" (generic, let user specify their niche)
        - If target_audience is Unknown → Ask "Who is your target audience for this piece?"
        - If key_message is Unknown → Ask "What's the main value or takeaway for viewers?"
        - If hook is Unknown → Ask "What's going to grab attention in the first 3 seconds?"
        - If structure is Unknown → Ask "How should we structure this? (hook → value → demo/explanation → CTA)"

        ATTACHMENT ANALYSIS GUIDELINES:
        - When the user shares images or videos, analyze them for content potential based on what they've told you about their niche
        - Focus on: visual elements, composition, potential for short-form content, how to use in videos
        - Suggest how to use the visuals in content (demos, comparisons, tutorials, etc.)
        - If MULTIPLE IMAGES are present, structure your reply as:
          1) "Image 1: <filename>" — content analysis
          2) "Image 2: <filename>" — content analysis
          [...]
          3) "Content Ideas" — how to combine these into engaging short-form content

        PLATFORM-SPECIFIC GUIDANCE:
        - Instagram Reels: 15-90 seconds, vertical format, trending audio, text overlays work well
        - TikTok: 15-60 seconds, vertical format, trending sounds, quick cuts, high energy
        - Both: Hook in first 3 seconds, clear value proposition, strong CTA

        CONVERSATION CONTEXT:
        {self._build_conversation_context(kwargs.get("conversation_history", []), kwargs.get("image_context", ""))}

        Be energetic, creative, and always focused on helping them create viral-worthy short-form content! Adapt to their niche naturally - only mention specific topics (like fitness, beauty, cooking, etc.) if they bring them up first. 🎬{rag_context_text}"""

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
                # Preface to enumerate images and require sectioned outputs
                filenames = [img.get("filename", "image.png") for img in image_data_list]
                if len(filenames) > 1:
                    listing = "\n".join([f"{i+1}) {name}" for i, name in enumerate(filenames)])
                    preface = (
                        "You will receive multiple images. Analyze each one in its own section and then add a Combined Summary.\n"
                        f"Images:\n{listing}\n"
                        "Format strictly: Image 1: <filename> … Image 2: <filename> … Combined Summary: …\n"
                    )
                else:
                    preface = ""
                user_content = [{"type": "text", "text": (preface + prompt) if preface else prompt}]
                
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
                print(f"🔍 [WebSearch] Web search disabled by user")
            elif enable_web_search is True:
                # User explicitly enabled web search - ALWAYS search using their query
                web_search_function = self._get_web_search_function(user_query=prompt)
                tools = [web_search_function] if web_search_function else None
                
                if tools:
                    # Force search by requiring the function to be called with user's query
                    tool_choice = {"type": "function", "function": {"name": "internet_search"}}
                    print(f"🔍 [WebSearch] Web search ENABLED by user - will search with query: '{prompt[:100]}...'")
                else:
                    tool_choice = None
            else:
                # enable_web_search is None - use default behavior (AI decides)
                force_search = self._should_force_search(prompt)
                web_search_function = self._get_web_search_function()
                tools = [web_search_function] if web_search_function else None
                
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
                    "max_completion_tokens": kwargs.get("max_tokens", 6000),
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
                response = openai.chat.completions.create(**api_params)
                
                print(f"✅ OpenAI response received (iteration {iteration})")
                
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
                            
                            # If web search was explicitly enabled, prefer user's original query
                            if enable_web_search is True and not search_query:
                                search_query = prompt
                                print(f"🔍 [WebSearch] Using user's original query as search query: '{search_query[:100]}...'")
                            
                            if search_query and web_search_service:
                                print(f"🔍 [WebSearch] Searching for: {search_query}")
                                # Always prioritize recent results when web search is enabled
                                search_results = web_search_service.search(
                                    search_query, 
                                    max_results=5, 
                                    prioritize_recent=True
                                )
                                
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
                        except Exception as e:
                            print(f"🔍 [WebSearch] Error processing search: {e}")
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": f"Error: {str(e)}"
                            })
                
                # Reset tool_choice for subsequent iterations (let AI decide)
                tool_choice = "auto"
            
            if final_response is None:
                # Fallback if we exhausted iterations
                final_response = message.content if message.content else "I apologize, but I encountered an issue processing your request."

            return {
                "response": final_response,
                "model_used": model_name,
                "tokens_used": response.usage.total_tokens if response.usage else 0
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
            
            # Build comprehensive script prompt for short-form content
            script_prompt = f"""You are a professional short-form video scriptwriter specializing in content creation for Instagram Reels and TikTok. Create an engaging 15-60 second video script based on the captured content data.

CONTENT DATA:
Content Type: {dossier_context.get('content_type', 'Not specified')}
Target Audience: {dossier_context.get('target_audience', 'Not specified')}
Key Message: {dossier_context.get('key_message', 'Not specified')}
Hook: {dossier_context.get('hook', 'Not specified')}
Structure: {dossier_context.get('structure', 'Not specified')}
Visual Elements: {dossier_context.get('visual_elements', 'Not specified')}

SCRIPT REQUIREMENTS:
1. Create a 15-60 second short-form video script (optimized for Instagram Reels/TikTok)
2. Use energetic, engaging tone appropriate for the content niche
3. Include visual cues, text overlay suggestions, and timing notes
4. Structure: HOOK (0-3s) → VALUE (3-15s) → DEMONSTRATION/EXPLANATION (15-45s) → CTA (45-60s)
5. Make it highly engaging and shareable
6. Include specific details from the content data above
7. Add trending format suggestions relevant to the content type

FORMAT:
[SHORT-FORM VIDEO SCRIPT]
[HOOK - 0-3 seconds]
[Visual: Eye-catching opening shot]
[Text Overlay]: "[Hook text]"
[Audio]: [Trending sound suggestion]
[Narrator]: "[Hook line]"

[VALUE - 3-15 seconds]
[Visual: [Specific visual suggestion]]
[Text Overlay]: "[Key message]"
[Narrator]: "[Value proposition]"

[DEMONSTRATION/EXPLANATION - 15-45 seconds]
[Visual: [Demo/visual explanation relevant to content type]]
[Text Overlay]: "[Step-by-step or key points]"
[Narrator]: "[Detailed explanation]"

[CTA - 45-60 seconds]
[Visual: [Closing shot]]
[Text Overlay]: "[Call to action]"
[Narrator]: "[Engagement CTA]"

[CAPTION SUGGESTION]:
[Engaging caption with emojis]

[HASHTAG SUGGESTIONS]:
[Relevant hashtags for the content niche]

Generate a complete, production-ready short-form video script optimized for virality."""

            # Use Claude Sonnet 4.5 for script generation (SOTA for structured long-form writing)
            if self.claude_available:
                response = self.claude_client.messages.create(
                    model="claude-sonnet-4-5-20250929",  # Latest Claude Sonnet 4.5 model (per Anthropic API docs)
                    max_tokens=kwargs.get("max_tokens", 8000),  # Claude Sonnet 4.5 supports up to 64K tokens out
                    temperature=kwargs.get("temperature", 0.7),
                    messages=[
                        {"role": "user", "content": script_prompt}
                    ]
                )

                return {
                    "response": response.content[0].text,
                    "model_used": "claude-sonnet-4-5-20250929",
                    "tokens_used": response.usage.input_tokens + response.usage.output_tokens,
                    "script_type": "video_tutorial",
                    "estimated_duration": "3-5 minutes"
                }
            else:
                # Fallback to GPT-4.1 (flagship for deep text generation)
                response = openai.chat.completions.create(
                    model="gpt-4.1",
                    messages=[
                        {"role": "system", "content": "You are a professional short-form video scriptwriter specializing in content creation for Instagram Reels and TikTok. Create engaging, high-energy scripts optimized for virality and engagement across any niche."},
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
            # Fallback to Claude Sonnet 4.5 if GPT-4o fails
            if self.claude_available:
                try:
                    response = self.claude_client.messages.create(
                        model="claude-sonnet-4-5-20250929",  # Latest Claude Sonnet 4.5 model (per Anthropic API docs)
                        max_tokens=kwargs.get("max_tokens", 3000),
                        temperature=kwargs.get("temperature", 0.8),
                        messages=[
                            {"role": "user", "content": f"Generate a detailed, cinematic scene based on: {prompt}"}
                        ]
                    )

                    return {
                        "response": response.content[0].text,
                        "model_used": "claude-sonnet-4-5-20250929",
                        "tokens_used": response.usage.input_tokens + response.usage.output_tokens
                    }
                except Exception as claude_error:
                    raise Exception(f"Both GPT-4.1 and Claude failed: GPT-4.1 error: {str(e)}, Claude error: {str(claude_error)}")
            else:
                raise Exception(f"GPT-4.1 scene generation error: {str(e)}")
    

# Global instance
ai_manager = AIModelManager()

