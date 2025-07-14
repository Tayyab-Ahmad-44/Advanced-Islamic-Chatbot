
import logging

from qdrant_client import QdrantClient

from schemas.data_classes.langraph_state import LangraphState
from schemas.data_classes.content_type import ContentType


class QdrantService:
    def __init__(self, qdrant_configs, embeddings):

        self.qdrant_clients = {}
        self.collection_configs = {}
        self.embeddings = embeddings
        
        # Create separate Qdrant clients for each content type
        for content_type, config in qdrant_configs.items():
            self.qdrant_clients[content_type] = QdrantClient(
                url=config["url"], 
                api_key=config["api_key"]
            )
            self.collection_configs[content_type] = config["collection"]





    def retrieve_documents(self, state: LangraphState, content_type: ContentType) -> LangraphState:
        """
        Generic document retrieval function with enhanced context awareness
        """
        try:
            content_type_value = content_type.value
            # Get the appropriate client and collection for this content type
            if content_type_value not in self.qdrant_clients:
                logging.warning(f"No Qdrant client configured for {content_type_value}")
                return state

            qdrant_client = self.qdrant_clients[content_type_value]
            collection_name = self.collection_configs[content_type_value]
            
            # Generate query embedding
            query_embedding = self.embeddings.embed_query(state.user_query)
            
            # Search in Qdrant
            search_results = qdrant_client.search(
                collection_name=collection_name,
                query_vector=query_embedding,
                limit=5,
                with_payload=True,
                with_vectors=False
            )
            
            # print("\n\n\n\n\n", search_results, "\n\n\n\n")
            
            # Format retrieved documents
            documents = []
            for result in search_results:
                doc = {
                    'content': result.payload.get('page_content', ''),
                    'metadata': result.payload.get('metadata', {}),
                    'score': result.score,
                    'source': content_type_value
                }
                documents.append(doc)
                

            print("\n\n\nDocuments: ", documents, "\n\n\n")


            # Store documents by source type
            if content_type_value not in state.retrieved_documents:
                state.retrieved_documents[content_type_value] = []
            state.retrieved_documents[content_type_value].extend(documents)

            logging.info(f"Retrieved {len(documents)} documents from {content_type_value}")

        except Exception as e:
            logging.error(f"Error retrieving documents from {content_type_value}: {e}")
            if not state.error_message:
                state.error_message = f"Error retrieving documents from {content_type_value}: {str(e)}"
        
        return state





    def fallback_retrieval(self, state: LangraphState) -> LangraphState:
        """
        Fallback node that searches across all collections when GENERAL is specified
        """
        try:
            # Search in all collections if no specific sources were identified
            for content_type_value, qdrant_client in self.qdrant_clients.items():
                try:
                    collection_name = self.collection_configs[content_type_value]
                    query_embedding = self.embeddings.embed_query(state.user_query)
                    
                    search_results = qdrant_client.search(
                        collection_name=collection_name,
                        query_vector=query_embedding,
                        limit=3,
                        with_payload=True,
                        with_vectors=False
                    )
                    
                    documents = []
                    for result in search_results:
                        doc = {
                            'content': result.payload.get('content', ''),
                            'metadata': result.payload.get('metadata', {}),
                            'score': result.score,
                            'source': content_type_value
                        }
                        documents.append(doc)
                    
                    if content_type_value not in state.retrieved_documents:
                        state.retrieved_documents[content_type_value] = []
                    state.retrieved_documents[content_type_value].extend(documents)
                        
                except Exception as e:
                    logging.warning(f"Error searching in {content_type_value}: {e}")
                    continue
            
            # Mark all sources as completed for fallback
            state.completed_sources.update([ContentType.QURAN, ContentType.HADITH, ContentType.TAFSEER])
            logging.info(f"Fallback retrieved documents from {len(state.retrieved_documents)} sources")
            
        except Exception as e:
            logging.error(f"Error in fallback retrieval: {e}")
            state.error_message = f"Fallback retrieval failed: {str(e)}"
        
        return state
