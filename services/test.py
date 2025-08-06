from sentence_transformers import SentenceTransformer, CrossEncoder

bi_encoder = SentenceTransformer('all-MiniLM-L6-v2')
cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')


query = "What's the capital of France?"
documents = [
    "Paris is the capital of France.",
    "Berlin is the capital of Germany.",
    "The Eiffel Tower is located in Paris.",
    "France is a country in Europe."
]

# Embedding with bi-encoder
q_vec = bi_encoder.encode(query)
d_vec = bi_encoder.encode(doc)

# Scoring with cross-encoder
score = cross_encoder.predict([[query, doc]])

print("Cross-encoder score:", score)


