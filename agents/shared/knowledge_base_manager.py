"""Foundry IQ Knowledge Base Management — Create and populate knowledge bases.

This module provides utilities to:
1. Create a new Foundry IQ knowledge base
2. Upload documents (PDF, TXT, DOCX) to the knowledge base
3. Index and sync documents for retrieval
4. Reference the knowledge base in agent definitions

Usage:
    kb_manager = KnowledgeBaseManager(project_client, project_id)
    
    # Create a new KB
    kb = kb_manager.create_knowledge_base(
        display_name="sports-iq-concessions",
        description="Stadium layout and concession operator map"
    )
    
    # Upload documents
    kb_manager.upload_documents(
        kb_id=kb.id,
        file_paths=["stadium_layout.pdf", "concession_menu.txt"]
    )
    
    # Use in agent
    from azure.ai.projects.models import RetrievalAugmentedGenerationTool
    rag_tool = RetrievalAugmentedGenerationTool(knowledge_base_id=kb.id)
"""

from __future__ import annotations
import logging
import os
from pathlib import Path
from typing import Any

from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    KnowledgeBase,
    KnowledgeBaseDocument,
)

log = logging.getLogger(__name__)


class KnowledgeBaseManager:
    """Manage Foundry IQ knowledge bases for Sports-IQ agents."""

    def __init__(self, project_client: AIProjectClient, project_id: str):
        """
        Initialize the knowledge base manager.
        
        Args:
            project_client: AIProjectClient from azure-ai-projects
            project_id: Foundry project ID
        """
        self.client = project_client
        self.project_id = project_id

    def create_knowledge_base(
        self,
        display_name: str,
        description: str | None = None,
    ) -> KnowledgeBase:
        """
        Create a new Foundry IQ knowledge base.
        
        Args:
            display_name: Human-readable KB name (e.g., "sports-iq-stadium-concessions")
            description: Optional description of the knowledge base content
            
        Returns:
            KnowledgeBase object with id, display_name, created_at
            
        Example:
            kb = manager.create_knowledge_base(
                display_name="stadium-layout-kb",
                description="Fictional venue sections, capacities, and concession zones"
            )
            print(f"Created KB: {kb.id}")
        """
        try:
            log.info(f"Creating knowledge base: {display_name}")
            
            kb = self.client.knowledge_bases.create(
                display_name=display_name,
                description=description,
            )
            
            log.info(f"✓ Knowledge base created: {kb.id}")
            return kb
        except Exception as exc:
            log.exception(f"Failed to create knowledge base '{display_name}'")
            raise

    def upload_documents(
        self,
        kb_id: str,
        file_paths: list[str],
        sync: bool = True,
    ) -> list[KnowledgeBaseDocument]:
        """
        Upload documents to a knowledge base.
        
        Args:
            kb_id: Knowledge base ID (from create_knowledge_base)
            file_paths: List of local file paths (PDF, TXT, DOCX, MD)
            sync: If True, wait for indexing to complete
            
        Returns:
            List of KnowledgeBaseDocument objects
            
        Example:
            docs = manager.upload_documents(
                kb_id="kb-12345",
                file_paths=[
                    "stadium_sections.pdf",
                    "concession_menu.txt",
                    "vendor_map.docx"
                ]
            )
            for doc in docs:
                print(f"Uploaded: {doc.name} ({doc.status})")
        """
        uploaded_docs = []
        
        for file_path in file_paths:
            try:
                file_path = Path(file_path)
                if not file_path.exists():
                    log.warning(f"File not found: {file_path}")
                    continue
                
                log.info(f"Uploading: {file_path.name}")
                
                with open(file_path, "rb") as f:
                    doc = self.client.knowledge_bases.upload_document(
                        kb_id=kb_id,
                        file_path=file_path,
                    )
                
                uploaded_docs.append(doc)
                log.info(f"✓ Uploaded: {doc.name} (status: {doc.status})")
                
            except Exception as exc:
                log.exception(f"Failed to upload document: {file_path}")
                continue
        
        # Optionally wait for indexing
        if sync and uploaded_docs:
            log.info("Waiting for document indexing...")
            self._wait_for_indexing(kb_id, uploaded_docs)
        
        return uploaded_docs

    def _wait_for_indexing(
        self,
        kb_id: str,
        docs: list[KnowledgeBaseDocument],
        timeout_seconds: int = 300,
    ) -> None:
        """
        Wait for documents to be indexed (internal helper).
        
        Args:
            kb_id: Knowledge base ID
            docs: List of documents to monitor
            timeout_seconds: Max time to wait
        """
        import time
        
        start = time.time()
        doc_ids = {d.id for d in docs}
        
        while time.time() - start < timeout_seconds:
            # Poll document status
            indexed_count = 0
            failed_count = 0
            
            for doc_id in doc_ids:
                try:
                    status = self.client.knowledge_bases.get_document_status(
                        kb_id=kb_id,
                        document_id=doc_id,
                    )
                    
                    if status.status == "indexed":
                        indexed_count += 1
                    elif status.status == "failed":
                        failed_count += 1
                        log.warning(f"Document {doc_id} failed to index: {status.error}")
                
                except Exception as e:
                    log.warning(f"Error checking document status: {e}")
            
            if indexed_count + failed_count == len(doc_ids):
                log.info(f"✓ Indexing complete: {indexed_count} indexed, {failed_count} failed")
                return
            
            log.debug(f"Indexing progress: {indexed_count}/{len(doc_ids)} indexed")
            time.sleep(5)
        
        log.warning(f"Indexing timeout after {timeout_seconds}s")

    def list_knowledge_bases(self) -> list[KnowledgeBase]:
        """
        List all knowledge bases in the project.
        
        Returns:
            List of KnowledgeBase objects
        """
        try:
            kbs = self.client.knowledge_bases.list()
            log.info(f"Found {len(kbs)} knowledge bases")
            return kbs
        except Exception as exc:
            log.exception("Failed to list knowledge bases")
            raise

    def get_knowledge_base(self, kb_id: str) -> KnowledgeBase:
        """Get a knowledge base by ID."""
        try:
            kb = self.client.knowledge_bases.get(kb_id)
            log.info(f"Retrieved KB: {kb.display_name}")
            return kb
        except Exception as exc:
            log.exception(f"Failed to retrieve KB {kb_id}")
            raise

    def delete_knowledge_base(self, kb_id: str) -> None:
        """Delete a knowledge base (CAUTION: irreversible)."""
        try:
            self.client.knowledge_bases.delete(kb_id)
            log.info(f"Deleted KB: {kb_id}")
        except Exception as exc:
            log.exception(f"Failed to delete KB {kb_id}")
            raise


# ── Convenience function for bootstrap ───────────────────────────────────────

def bootstrap_knowledge_base(
    kb_display_name: str,
    kb_description: str,
    document_dir: str,
    file_extensions: list[str] | None = None,
) -> str:
    """
    One-shot bootstrap: create KB and upload all docs from a directory.
    
    Args:
        kb_display_name: Name for the new knowledge base
        kb_description: Description
        document_dir: Directory containing documents to upload
        file_extensions: List of extensions to include (default: ['.pdf', '.txt', '.md', '.docx'])
        
    Returns:
        Knowledge base ID
        
    Example:
        kb_id = bootstrap_knowledge_base(
            kb_display_name="sports-iq-stadium-docs",
            kb_description="Stadium layout and concession data",
            document_dir="./docs/stadium",
            file_extensions=['.pdf', '.txt']
        )
        print(f"Ready to use KB ID: {kb_id}")
    """
    from agents.shared.config import config
    
    if file_extensions is None:
        file_extensions = ['.pdf', '.txt', '.md', '.docx']
    
    # Initialize Foundry client
    credential = DefaultAzureCredential()
    project_client = AIProjectClient(
        endpoint=config.AZURE_AI_PROJECT_ENDPOINT,
        credential=credential,
    )
    
    # Create KB manager
    manager = KnowledgeBaseManager(project_client, config.AZURE_AI_PROJECT_ID)
    
    # Create KB
    kb = manager.create_knowledge_base(
        display_name=kb_display_name,
        description=kb_description,
    )
    log.info(f"Created knowledge base with ID: {kb.id}")
    
    # Collect documents
    doc_dir = Path(document_dir)
    docs_to_upload = [
        str(f) for f in doc_dir.rglob('*')
        if f.is_file() and f.suffix.lower() in file_extensions
    ]
    
    if docs_to_upload:
        log.info(f"Found {len(docs_to_upload)} documents to upload")
        manager.upload_documents(kb_id=kb.id, file_paths=docs_to_upload, sync=True)
    else:
        log.warning(f"No documents found in {document_dir}")
    
    return kb.id
