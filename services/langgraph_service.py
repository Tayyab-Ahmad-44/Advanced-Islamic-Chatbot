
import logging

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from services.qdrant_service import QdrantService
from services.open_ai_service import openai_service
from schemas.data_classes.content_type import ContentType
from schemas.data_classes.langraph_state import LangraphState



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

        self.graph = self._create_graph()





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
        try:
            if state.error_message and not state.retrieved_documents:
                state.final_response = f"I apologize, but I encountered an error: {state.error_message}"
                return state

            # Prepare comprehensive context from all sources
            context_sections = []
            
            for source_type, documents in state.retrieved_documents.items():
                if documents:
                    source_context = f"\n--- {source_type.upper()} SOURCES ---\n"
                    for i, doc in enumerate(documents[:3], 1):
                        source_context += f"{i}. {doc['content']}\n"
                    context_sections.append(source_context)
            
            full_context = "\n".join(context_sections)

            response = openai_service.generate_response(state.user_query, full_context)

            state.final_response = response['message']

        except Exception as e:
            logging.error(f"Error generating response: {e}")
            state.final_response = f"I apologize, but I encountered an error while generating the response: {str(e)}"

        return state





    def _route_to_next_source(self, state: LangraphState) -> str:
        """
        Route to the next required source based on classification order
        """
        # Check if we should use fallback (GENERAL source)
        if ContentType.GENERAL in state.required_sources:
            return "fallback_retrieval"
        
        # Check if we have more sources to process
        if state.current_source_index < len(state.required_sources):
            current_source = state.required_sources[state.current_source_index]
            
            if current_source == ContentType.QURAN:
                return "retrieve_quran"
            elif current_source == ContentType.HADITH:
                return "retrieve_hadith"
            elif current_source == ContentType.TAFSEER:
                return "retrieve_tafseer"
        
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
        workflow.add_node("classify_query", self._classify_multi_source_query)
        workflow.add_node("route_to_source", self._route_to_next_source)  
        workflow.add_node("retrieve_quran", self._retrieve_from_quran)
        workflow.add_node("retrieve_hadith", self._retrieve_from_hadith)
        workflow.add_node("retrieve_tafseer", self._retrieve_from_tafseer)
        workflow.add_node("fallback_retrieval", self._fallback_retrieval)
        workflow.add_node("generate_response", self._generate_comprehensive_response)

        # Set entry point
        workflow.set_entry_point("classify_query")

        # Route from classification to routing logic
        workflow.add_edge("classify_query", "route_to_source")

        # Route from routing node to appropriate source
        workflow.add_conditional_edges(
            "route_to_source",
            self._route_to_next_source,
            {
                "retrieve_quran": "retrieve_quran",
                "retrieve_hadith": "retrieve_hadith", 
                "retrieve_tafseer": "retrieve_tafseer",
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
        
        # Fallback goes directly to response
        workflow.add_edge("fallback_retrieval", "generate_response")
        
        # End after response generation
        workflow.add_edge("generate_response", END)
        
        # Compile the graph
        return workflow.compile(checkpointer=MemorySaver())





    def query(self, user_query: str, base_prompt: str = "") -> str:
        """
        Main function to process user query with multi-source retrieval
        
        Args:
            user_query: The user's question
            base_prompt: Base prompt to be enhanced with retrieved context
            
        Returns:
            Generated response from the system
        """
        # Create initial state
        initial_state = LangraphState(
            user_query=user_query,
            base_prompt=base_prompt or "Please provide a comprehensive Islamic answer to the following question:",
            required_sources=[],
            completed_sources=set(),
            retrieved_documents={},
            final_response="",
            current_source_index=0
        )
        
        # Run the graph
        final_state = self.graph.invoke(initial_state)
        
        return final_state['final_response']
