import os
import json
import numpy as np
from pathlib import Path
from sklearn.metrics.pairwise import cosine_similarity
import logging
from transformers import AutoTokenizer, AutoModel
import torch

logger = logging.getLogger(__name__)

class VectorDBService:
    def __init__(self):
        self.data_path = Path("./data/vector_db")
        self.data_path.mkdir(parents=True, exist_ok=True)
        self.vectors_file = self.data_path / "vectors.json"
        self.vectors = self._load_vectors()
        
        # Initialize model for embeddings
        try:
            self.tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
            self.model = AutoModel.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            self.model.to(self.device)
            logger.info(f"Vector DB initialized with model on {self.device}")
        except Exception as e:
            logger.error(f"Error initializing embedding model: {e}")
            self.tokenizer = None
            self.model = None
    
    def _load_vectors(self):
        """Load vectors from file."""
        if not self.vectors_file.exists():
            return []
        
        try:
            with open(self.vectors_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading vectors: {e}")
            return []
    
    def _save_vectors(self):
        """Save vectors to file."""
        try:
            with open(self.vectors_file, 'w') as f:
                json.dump(self.vectors, f)
            return True
        except Exception as e:
            logger.error(f"Error saving vectors: {e}")
            return False
    
    def get_embedding(self, text):
        """Convert text to embedding vector."""
        if not self.tokenizer or not self.model:
            logger.error("Embedding model not initialized")
            return None
        
        try:
            # Tokenize and get model outputs
            inputs = self.tokenizer(text, padding=True, truncation=True, return_tensors="pt").to(self.device)
            with torch.no_grad():
                outputs = self.model(**inputs)
            
            # Mean pooling
            attention_mask = inputs['attention_mask']
            token_embeddings = outputs.last_hidden_state
            input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
            embeddings = torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)
            
            # Convert to list for JSON serialization
            return embeddings[0].cpu().numpy().tolist()
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None
    
    def add_document(self, text, metadata=None):
        """Add a document to the vector store."""
        if not metadata:
            metadata = {}
        
        embedding = self.get_embedding(text)
        if not embedding:
            return False
        
        doc_id = len(self.vectors)
        self.vectors.append({
            "id": doc_id,
            "text": text,
            "embedding": embedding,
            "metadata": metadata
        })
        
        return self._save_vectors()
    
    def similarity_search(self, query, top_k=3):
        """Search for similar documents."""
        if not self.vectors:
            return []
        
        query_embedding = self.get_embedding(query)
        if not query_embedding:
            return []
        
        # Convert query embedding to numpy array
        query_embedding = np.array(query_embedding).reshape(1, -1)
        
        # Get all document embeddings
        doc_embeddings = np.array([doc["embedding"] for doc in self.vectors])
        
        # Calculate similarities
        similarities = cosine_similarity(query_embedding, doc_embeddings)[0]
        
        # Get indices of top_k most similar documents
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        # Return top_k documents with their similarity scores
        results = []
        for idx in top_indices:
            doc = self.vectors[idx]
            results.append({
                "id": doc["id"],
                "text": doc["text"],
                "similarity": float(similarities[idx]),
                "metadata": doc["metadata"]
            })
        
        return results 