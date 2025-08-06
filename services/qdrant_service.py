

import logging
from sentence_transformers import CrossEncoder

from qdrant_client import QdrantClient

from schemas.data_classes.langraph_state import LangraphState
from schemas.data_classes.content_type import ContentType


class QdrantService:
    def __init__(self, qdrant_configs, embeddings, reranker_model_name="cross-encoder/ms-marco-MiniLM-L-6-v2"):

        self.qdrant_clients = {}
        self.collection_configs = {}
        self.embeddings = embeddings
        
        # Initialize reranker model
        self.reranker = CrossEncoder(reranker_model_name)
        
        # Create separate Qdrant clients for each content type
        for content_type, config in qdrant_configs.items():
            self.qdrant_clients[content_type] = QdrantClient(
                url=config["url"], 
                api_key=config["api_key"]
            )
            self.collection_configs[content_type] = config["collection"]


    def _get_content_type_limit(self, content_type: ContentType) -> int:
        """Get retrieval limit based on content type"""
        limits = {
            ContentType.QURAN: 5,
            ContentType.TAFSEER: 3,      # Conservative due to huge content
            ContentType.HADITH: 6,
            ContentType.GENERAL: 10
        }
        return limits.get(content_type, 8)  # Default fallback


    def _rerank_documents(self, query: str, documents: list, top_k: int = None) -> list:
        """
        Rerank documents using cross-encoder model
        """
        if not documents:
            return documents
            
        # Prepare query-document pairs for reranking
        query_doc_pairs = [(query, doc['content']) for doc in documents]
        
        # Get relevance scores from cross-encoder
        relevance_scores = self.reranker.predict(query_doc_pairs)
        
        # Add rerank scores to documents
        for i, doc in enumerate(documents):
            doc['rerank_score'] = float(relevance_scores[i])
        
        # Sort by rerank score (descending)
        reranked_docs = sorted(documents, key=lambda x: x['rerank_score'], reverse=True)
        
        # Return top_k if specified
        if top_k:
            return reranked_docs[:top_k]
        
        return reranked_docs


    def retrieve_documents(self, state: LangraphState, content_type: ContentType) -> LangraphState:
        """
        Generic document retrieval function with enhanced context awareness and reranking
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
            
            limit = self._get_content_type_limit(content_type)
            # Search in Qdrant - retrieve more documents for reranking
            search_results = qdrant_client.search(
                collection_name=collection_name,
                query_vector=query_embedding,
                limit=limit * 2,  # Retrieve more documents for reranking
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
            
            # Rerank documents using cross-encoder
            reranked_documents = self._rerank_documents(state.user_query, documents, top_k=limit)

            print("\n\n\nReranked Documents: ", reranked_documents, "\n\n\n")

            # Store documents by source type
            if content_type_value not in state.retrieved_documents:
                state.retrieved_documents[content_type_value] = []
            
            state.retrieved_documents[content_type_value].extend(reranked_documents)

            logging.info(f"Retrieved and reranked {len(reranked_documents)} documents from {content_type_value}")

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
                        limit=6,  # Retrieve more for reranking
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
                    
                    # Rerank documents for this source
                    reranked_documents = self._rerank_documents(state.user_query, documents, top_k=3)
                    
                    if content_type_value not in state.retrieved_documents:
                        state.retrieved_documents[content_type_value] = []
                    state.retrieved_documents[content_type_value].extend(reranked_documents)
                        
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