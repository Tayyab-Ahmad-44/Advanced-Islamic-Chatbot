
import logging
logger = logging.getLogger(__name__)

from tavily import TavilyClient
from langgraph.graph import StateGraph, END

from core.config import settings
from services.qdrant_service import QdrantService
from services.open_ai_service import openai_service
from schemas.data_classes.content_type import ContentType
from schemas.data_classes.langraph_state import LangraphState
from services.deepL_service import Deepl_Service


deepl_services = Deepl_Service()


class LanggraphService:
    def __init__(
        self,
        qdrant_configs,
    ):
        """
        Initialize the Langgraph for Islamic RAG System
        """

        self.embeddings = openai_service.embeddings

        self.qdrant_service = QdrantService(qdrant_configs, self.embeddings)
        
        self.tavily_client = TavilyClient(api_key=settings.TAVILY_API_KEY)

        self.graph = self._create_graph()

        self.deepl_services = Deepl_Service()
        
        # self.is_english_query =




    def _classify_multi_source_query(self, state: LangraphState) -> LangraphState:
        """
        Advanced LLM-based classification using structured output
        """
        try:
            # Get structured classification from LLM            
            classification_response = openai_service.classify_multi_source_query(state.user_query)
            if classification_response['status'] == 'error':
                state.required_sources = [ContentType.GENERAL]
                state.current_source_index = 0


            classification = classification_response['message']

            # Convert string sources to ContentType enum in order
            required_sources = []
            for source in classification.required_sources:
                source_clean = source.lower().strip()
                if source_clean == "quran":
                    required_sources.append(ContentType.QURAN)
                elif source_clean == "hadith":
                    required_sources.append(ContentType.HADITH)
                elif source_clean == "tafseer":
                    required_sources.append(ContentType.TAFSEER)
                elif source_clean == "general_islamic_info":
                    required_sources.append(ContentType.GENERAL)


            # If no valid sources identified, use general fallback
            if not required_sources:
                required_sources.append(ContentType.GENERAL)


            state.required_sources = required_sources
            state.current_source_index = 0  # Reset index


            # Log the classification details
            logging.info("LLM Classification Results:")
            logging.info(f"  - Required sources (in order): {[s.value for s in required_sources]}")
            logging.info(f"  - Reasoning: {classification.reasoning}")
            
        except Exception as e:
            logging.error(f"Error in LLM classification: {e}")
            # Fallback to general classification
            state.required_sources = [ContentType.GENERAL]
            state.current_source_index = 0
            logging.info("Fallback: Using general classification due to error")
        
        return state





    def _web_search_and_store(self, state: LangraphState) -> LangraphState:
        """
        Perform web search using Tavily and store results in vector database
        """
        try:
            if not self.tavily_client:
                logging.warning("Tavily client not initialized, skipping web search")
                return state
                
            # Perform web search
            search_results = self.tavily_client.search(
                query=f"{state.user_query} in Islam.",
                search_depth="advanced",
                max_results=1,                            #updated
                include_answer=True,
                include_raw_content=True,
                
            )

            # Process and store search results
            web_documents = []
            for result in search_results.get('results', []):
                doc_content = {
                    'content': result.get('content', ''),
                    'url': result.get('url', ''),
                    'title': result.get('title', '')
                }
                web_documents.append(doc_content)

            
            # Store in vector database (you might want to create a separate collection for web results)
            # Or store in state for later use
            if not hasattr(state, 'web_search_results'):
                state.web_search_results = []
            state.web_search_results.extend(web_documents)
            
            logging.info(f"Retrieved {len(web_documents)} web search results")
            
        except Exception as e:
            logging.error(f"Error in web search: {e}")
            if not hasattr(state, 'web_search_results'):
                state.web_search_results = []
        
        return state




    def _retrieve_from_quran(self, state: LangraphState) -> LangraphState:
        """
        Retrieve documents from Quran vector store
        """
        state = self._retrieve_documents(state, ContentType.QURAN)
        state.completed_sources.add(ContentType.QURAN)
        state.current_source_index += 1
        return state





    def _retrieve_from_hadith(self, state: LangraphState) -> LangraphState:
        """
        Retrieve documents from Hadith vector store
        """
        state = self._retrieve_documents(state, ContentType.HADITH)
        state.completed_sources.add(ContentType.HADITH)
        state.current_source_index += 1
        return state





    def _retrieve_from_tafseer(self, state: LangraphState) -> LangraphState:
        """
        Retrieve documents from Tafseer vector store
        """
        state = self._retrieve_documents(state, ContentType.TAFSEER)
        state.completed_sources.add(ContentType.TAFSEER)
        state.current_source_index += 1
        return state





    def _retrieve_from_general(self, state: LangraphState) -> LangraphState:
        """
        Retrieve documents from General Islamic Info vector store
        """
        state = self._retrieve_documents(state, ContentType.GENERAL)
        state.completed_sources.add(ContentType.GENERAL)
        state.current_source_index += 1
        return state





    def _retrieve_documents(self, state: LangraphState, content_type: ContentType) -> LangraphState:
        """
        Generic document retrieval function with enhanced context awareness
        """
        return self.qdrant_service.retrieve_documents(state, content_type)





    def _fallback_retrieval(self, state: LangraphState) -> LangraphState:
        """
        Fallback node that searches across all collections when GENERAL is specified
        """
        return self.qdrant_service.fallback_retrieval(state)



    def _generate_comprehensive_response(self, state: LangraphState) -> LangraphState:
        """
        Generate final response using all retrieved context from multiple sources
        """
        
        logger.info("Starting _generate_comprehensive_response")
        
        try:
            if state.error_message and not state.retrieved_documents:
                logger.warning(f"Encountered error with no documents: {state.error_message}")
                state.final_response = f"I apologize, but I encountered an error: {state.error_message}"
                return state

            query_lang = state.detected_language
            logger.info(f"Detected query language inside gen_comprehensive_response function: {query_lang.upper()}")

            # Prepare comprehensive context from all sources
            if query_lang.upper() != "EN":
                
                translation_batches = []  # Store {content: text, source_info: info} for each batch
                context_items = []  # Store all context items in order with their type
                
                # Handle web search results
                if hasattr(state, 'web_search_results') and state.web_search_results:
                    logger.info("Adding web search results to translation batch")
                    
                    # Extract only the content that needs translation
                    web_contents_to_translate = []
                    web_metadata = []
                    
                    for i, doc in enumerate(state.web_search_results):
                        # Only translate the content, keep title and URL separate
                        if doc.get('content'):
                            web_contents_to_translate.append(doc['content'])
                            web_metadata.append({
                                'index': i,
                                'title': doc.get('title', ''),
                                'url': doc.get('url', '')
                            })
                    
                    if web_contents_to_translate:
                        # Join only content for translation
                        web_content_batch = "\n\n===CONTENT_SEPARATOR===\n\n".join(web_contents_to_translate)
                        translation_batches.append({
                            'content': web_content_batch,
                            'source_info': {
                                'type': 'web_search',
                                'metadata': web_metadata,
                                'count': len(web_contents_to_translate)
                            }
                        })
                        context_items.append({'type': 'translate', 'batch_index': len(translation_batches) - 1})
                
                # Process retrieved documents by source type
                for source_type, documents in state.retrieved_documents.items():
                    logger.debug(f"Processing source_type: {source_type} with {len(documents)} documents")
                    
                    if documents:
                        if source_type == 'quran':
                            # Quran uses Russian from metadata - no translation needed
                            quran_source_context = f"\n--- {source_type.upper()} SOURCES ---\n"
                            
                            for i, doc in enumerate(documents):
                                ru_text = doc['metadata'].get('ru_translation', 'No RU translation available')
                                metadata_copy = doc["metadata"].copy()
                                metadata_copy.pop("Tafsir", None)  # Remove Tafsir safely
                                quran_source_context += f"{i}.\nRU_Translation: {ru_text}\nMetadata: {metadata_copy}\n\n"
                                
                            context_items.append({'type': 'direct', 'content': quran_source_context})

                        elif source_type == 'tafseer':
                            # Tafseer uses metadata directly - no translation needed
                            tafseer_source_context = f"\n--- {source_type.upper()} SOURCES ---\n"
                            
                            for i, doc in enumerate(documents):
                                
                                metadata = doc.get('metadata', {})
                                
                                clean_metadata = {k: v for k, v in metadata.items()
                                                  if k not in ['As_Saadi_Tafseer', 'abu_Adil_tafsir', 'Ibni_kathir_quran_tafsir', 'ayah_translation', 'surah_number', 'En_tafsir_source', 'En_source_url', 'abu_Adil_tafsir_source', 'Ibni_kathir_tafsir_source', 'tafsir_Source', 'As-Saadi_tafsir_source',   ]
                                                  }

                                                
                                tafseer_keys = ['As_Saadi_Tafseer', 'abu_Adil_tafsir', 'Ibni_kathir_quran_tafsir']
                                
                                for key in tafseer_keys:
                                    if key in metadata and metadata[key]:  # Check if value exists and not empty
                                        
                                        clean_metadata_copy = clean_metadata.copy() 
                                        clean_metadata_copy["Tafsir_Source"] = key
                                        
                                        tafseer_source_context += f"Tafseer_Content: {metadata[key]}\nMetadata: {clean_metadata_copy}\n\n"
                                        
                                            
                            context_items.append({'type': 'direct', 'content': tafseer_source_context})
                        
                        elif source_type == 'hadith':
                            # Hadith content needs translation - extract only content
                            hadith_contents_to_translate = []
                            hadith_metadata = []
                            
                            for i, doc in enumerate(documents):
                                if doc.get('content'):
                                    hadith_contents_to_translate.append(doc['content'])
                                    hadith_metadata.append({
                                        'index': i,
                                        'metadata': doc.get('metadata', {})
                                    })
                            
                            if hadith_contents_to_translate:
                                # Join only content for translation
                                hadith_content_batch = "\n\n===CONTENT_SEPARATOR===\n\n".join(hadith_contents_to_translate)
                                translation_batches.append({
                                    'content': hadith_content_batch,
                                    'source_info': {
                                        'type': 'hadith',
                                        'metadata': hadith_metadata,
                                        'count': len(hadith_contents_to_translate)
                                    }
                                })
                                logger.info("Adding hadith to translation batch")
                                context_items.append({'type': 'translate', 'batch_index': len(translation_batches) - 1})
                        
                        elif source_type == 'general_islamic_info':
                            # General content needs translation - extract only content
                            general_contents_to_translate = []
                            general_metadata = []
                            
                            for i, doc in enumerate(documents):
                                if doc.get('content'):
                                    general_contents_to_translate.append(doc['content'])
                                    general_metadata.append({
                                        'index': i,
                                        'metadata': doc.get('metadata', {})
                                    })
                            
                            if general_contents_to_translate:
                                # Join only content for translation
                                general_content_batch = "\n\n===CONTENT_SEPARATOR===\n\n".join(general_contents_to_translate)
                                translation_batches.append({
                                    'content': general_content_batch,
                                    'source_info': {
                                        'type': 'general_islamic_info',
                                        'metadata': general_metadata,
                                        'count': len(general_contents_to_translate)
                                    }
                                })
                                logger.info("Adding general Islamic info to translation batch")
                                context_items.append({'type': 'translate', 'batch_index': len(translation_batches) - 1})

                # Perform batch translation with improved strategy
                translated_batches = []
                if translation_batches:
                    logger.info(f"Translating {len(translation_batches)} batches...")
                    
                    for batch_idx, batch in enumerate(translation_batches):
                        try:
                            logger.info(f"Translating batch {batch_idx + 1}/{len(translation_batches)} for {batch['source_info']['type']}")
                            logger.debug(f"Original content to translate: {batch['content'][:200]}...")
                            
                            # Translate only the content
                            translated_content = self.deepl_services.translate_response(batch['content'], query_lang)
                            
                            logger.info(f"Batch {batch_idx + 1} translation completed successfully!")
                            logger.debug(f"Translated content: {translated_content[:200]}...")
                            
                            # Split translated content back
                            translated_parts = translated_content.split("\n\n===CONTENT_SEPARATOR===\n\n")
                            
                            # Validate translation
                            expected_parts = batch['source_info']['count']
                            if len(translated_parts) != expected_parts:
                                logger.warning(f"Expected {expected_parts} parts, got {len(translated_parts)} for batch {batch_idx}")
                                # If split failed, treat as single content
                                translated_parts = [translated_content]
                            
                            translated_batches.append({
                                'translated_parts': translated_parts,
                                'source_info': batch['source_info']
                            })
                            
                        except Exception as e:
                            logger.error(f"Translation failed for batch {batch_idx}: {str(e)}")
                            # Use original content if translation fails
                            original_parts = batch['content'].split("\n\n===CONTENT_SEPARATOR===\n\n")
                            translated_batches.append({
                                'translated_parts': original_parts,
                                'source_info': batch['source_info']
                            })
                
                # Reconstruct context with translated content
                final_context_sections = []
                translation_batch_index = 0
                
                for item in context_items:
                    if item['type'] == 'direct':
                        # Add direct content (no translation needed)
                        final_context_sections.append(item['content'])
                        
                    elif item['type'] == 'translate':
                        # Add translated content
                        batch_idx = item['batch_index']
                        if batch_idx < len(translated_batches):
                            translated_batch = translated_batches[batch_idx]
                            source_info = translated_batch['source_info']
                            translated_parts = translated_batch['translated_parts']
                            
                            # Reconstruct the section with translated content
                            if source_info['type'] == 'web_search':
                                section_content = f"\n--- WEB SEARCH RESULTS ---\n"
                                for i, (translated_part, meta) in enumerate(zip(translated_parts, source_info['metadata'])):
                                    section_content += f"{meta['index']}.\nTitle: {meta['title']}\nContent: {translated_part}\nURL: {meta['url']}\n\n"
                            
                            elif source_info['type'] == 'hadith':
                                section_content = f"\n--- HADITH SOURCES ---\n"
                                for i, (translated_part, meta) in enumerate(zip(translated_parts, source_info['metadata'])):
                                    section_content += f"\n{meta['index']}: Hadith_content: {translated_part}\nMetadata: {meta['metadata']}\n\n"
                            
                            elif source_info['type'] == 'general_islamic_info':
                                section_content = f"\n--- GENERAL_ISLAMIC_INFO SOURCES ---\n"
                                for i, (translated_part, meta) in enumerate(zip(translated_parts, source_info['metadata'])):
                                    section_content += f"\n{meta['index']}: General_content: {translated_part}\nMetadata: {meta['metadata']}\n\n"
                            
                            final_context_sections.append(section_content)
                            logger.debug(f"Added translated {source_info['type']} section")
                        else:
                            logger.warning(f"Missing translation for batch index {batch_idx}")

                full_context = "\n\n\n".join(final_context_sections)
                logger.info("Final context compiled successfully for non-English query")
                print(f"\n---------------------Russian_final_context-----------------------\n{full_context}")
                
                # Generate response using the prepared context
                logger.info("Sending Russian context to OpenAI for response generation")
                response = openai_service.generate_response(state.user_query, full_context, state.detected_language)
                state.final_response = response['message']
                logger.info("Russian Response generated successfully")
                
                
                

                            # ------ if EN Qury detected
            else:
                logger.info("Query is in English. Assembling context without translation.")
                context_sections = []
                
                # Add web search results if available
                if hasattr(state, 'web_search_results') and state.web_search_results:
                    web_context = "\n--- WEB SEARCH RESULTS ---\n"
                    
                    for i, doc in enumerate(state.web_search_results):
                        web_context += f"{i}.\nTitle: {doc['title']}\nContent: {doc['content']}\nURL: {doc['url']}\n\n"
                        
                    context_sections.append(web_context)
                
                # Add retrieved documents
                for source_type, documents in state.retrieved_documents.items():
                    if documents:
                        source_context = f"\n--- {source_type.upper()} SOURCES ---\n"
                        
                        for i, doc in enumerate(documents):
                            source_context += f"{i}.\nContent: {doc['content']}\nMetadata: {doc['metadata']}\n\n"
                        
                        context_sections.append(source_context)
                
                full_context = "\n".join(context_sections)
                logger.info("English context compiled successfully")

            # Generate response using the prepared context
            logger.info("Sending context to OpenAI for response generation")
            response = openai_service.generate_response(state.user_query, full_context, state.detected_language)
            state.final_response = response['message']
            logger.info("English Response generated successfully")


        except Exception as e:
            logger.error(f"Error in _generate_comprehensive_response: {str(e)}")
            error_msg = f"I apologize, but I encountered an error while generating the response: {str(e)}"
            
            # Translate error message for non-English queries
            if hasattr(state, 'detected_language') and state.detected_language.upper() != "EN":
                try:
                    error_msg = self.deepl_services.translate_response(error_msg, state.detected_language)
                except Exception as translation_error:
                    logger.error(f"Failed to translate error message: {translation_error}")
            
            state.final_response = error_msg

        return state
                    
  

    def _route_to_next_source(self, state: LangraphState) -> LangraphState:
        """
        Route to the next required source based on classification order
        This is now a regular node, not a conditional edge function
        """
        # Just return the state as-is, routing logic will be handled by conditional edges
        return state




 
    def _determine_next_route(self, state: LangraphState) -> str:
        """
        Determine the next route - this is the actual conditional edge function
        """

        # Check if we have more sources to process
        if state.current_source_index < len(state.required_sources):
            current_source = state.required_sources[state.current_source_index]

            if current_source == ContentType.QURAN:
                return "retrieve_quran"
            elif current_source == ContentType.HADITH:
                return "retrieve_hadith"
            elif current_source == ContentType.TAFSEER:
                return "retrieve_tafseer"
            elif current_source == ContentType.GENERAL:
                return "retrieve_general"
        
        # No more sources to process
        return "generate_response"





    def _should_continue_retrieval(self, state: LangraphState) -> str:
        """
        Determine if we should continue retrieving or move to response generation
        """
        # Check if we have more sources to process
        if state.current_source_index < len(state.required_sources):
            return "continue_retrieval"
        else:
            return "generate_response"





    def _create_graph(self) -> StateGraph:
        """
        Create the enhanced LangGraph workflow with proper sequential retrieval
        """
        # Create the state graph
        workflow = StateGraph(LangraphState)

        # Add nodes
        workflow.add_node("web_search", self._web_search_and_store)
        workflow.add_node("classify_query", self._classify_multi_source_query)
        workflow.add_node("route_to_source", self._route_to_next_source)  
        workflow.add_node("retrieve_quran", self._retrieve_from_quran)
        workflow.add_node("retrieve_hadith", self._retrieve_from_hadith)
        workflow.add_node("retrieve_tafseer", self._retrieve_from_tafseer)
        workflow.add_node("retrieve_general", self._retrieve_from_general)
        workflow.add_node("fallback_retrieval", self._fallback_retrieval)
        workflow.add_node("generate_response", self._generate_comprehensive_response)

        # Set entry point
        workflow.set_entry_point("web_search")

        # Route from web search to classification
        workflow.add_edge("web_search", "classify_query")

        # Route from classification to routing logic
        workflow.add_edge("classify_query", "route_to_source")

        # Route from routing node to appropriate source
        workflow.add_conditional_edges(
            "route_to_source",
            self._determine_next_route,
            {
                "retrieve_quran": "retrieve_quran",
                "retrieve_hadith": "retrieve_hadith", 
                "retrieve_tafseer": "retrieve_tafseer",
                "retrieve_general": "retrieve_general",
                "fallback_retrieval": "fallback_retrieval",
                "generate_response": "generate_response"
            }
        )

        # After each retrieval, route to next source or generate response
        workflow.add_conditional_edges(
            "retrieve_quran",
            self._should_continue_retrieval,
            {
                "continue_retrieval": "route_to_source",
                "generate_response": "generate_response"
            }
        )

        workflow.add_conditional_edges(
            "retrieve_hadith",
            self._should_continue_retrieval,
            {
                "continue_retrieval": "route_to_source",
                "generate_response": "generate_response"
            }
        )

        workflow.add_conditional_edges(
            "retrieve_tafseer",
            self._should_continue_retrieval,
            {
                "continue_retrieval": "route_to_source",
                "generate_response": "generate_response"
            }
        )
        
        workflow.add_conditional_edges(
            "retrieve_general",
            self._should_continue_retrieval,
            {
                "continue_retrieval": "route_to_source",
                "generate_response": "generate_response"
            }
        )

        # Fallback goes directly to response
        workflow.add_edge("fallback_retrieval", "generate_response")

        # End after response generation
        workflow.add_edge("generate_response", END)

        # Compile the graph without checkpointer
        return workflow.compile()





    def query(self, user_query: str, lang_detected: str, base_prompt: str = "") -> str:
        """
        Main function to process user query with multi-source retrieval
        
        Args:
            user_query: The user's question
            base_prompt: Base prompt to be enhanced with retrieved context
            
        Returns:
            Generated response from the system
        """
        try:
            # Create initial state
            initial_state = LangraphState(
                user_query=user_query,
                base_prompt=base_prompt or "Please provide a comprehensive Islamic answer to the following question:",
                required_sources=[],
                completed_sources=set(),
                retrieved_documents={},
                final_response="",
                current_source_index=0,
                detected_language=lang_detected  # <-- passed
            )
            logging.info(f"Langraph initial_state.detected_language: {initial_state.detected_language}")
            
            # Run the graph without configuration (no checkpointer)
            final_state = self.graph.invoke(initial_state)
            
            return final_state['final_response']
        except Exception as e:
            print("Error while Querying: ", e)
            return str(e)
