#!/usr/bin/env python
"""Bootstrap script: Create a Foundry IQ Knowledge Base and upload documents.

Usage:
    python scripts/setup_knowledge_base.py --kb-name "sports-iq-stadium" \
        --kb-desc "Stadium layout and concessions" \
        --doc-dir "./docs/stadium"

This script will:
  1. Create a new knowledge base in Foundry
  2. Upload all documents from the specified directory
  3. Wait for indexing to complete
  4. Print the KB ID for use in agent definitions
"""

import argparse
import sys
from pathlib import Path

# Add repo root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.shared.knowledge_base_manager import bootstrap_knowledge_base
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s'
)
log = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Create and populate a Foundry IQ Knowledge Base"
    )
    parser.add_argument(
        "--kb-name",
        required=True,
        help="Display name for the knowledge base (e.g., 'sports-iq-stadium')"
    )
    parser.add_argument(
        "--kb-desc",
        required=True,
        help="Description of the knowledge base content"
    )
    parser.add_argument(
        "--doc-dir",
        required=True,
        help="Directory containing documents to upload"
    )
    parser.add_argument(
        "--extensions",
        default=".pdf,.txt,.md,.docx",
        help="Comma-separated file extensions to include (default: .pdf,.txt,.md,.docx)"
    )
    
    args = parser.parse_args()
    
    # Validate directory
    doc_dir = Path(args.doc_dir)
    if not doc_dir.exists():
        log.error(f"Directory not found: {doc_dir}")
        sys.exit(1)
    
    # Parse extensions
    extensions = [f".{ext.strip('.')}" for ext in args.extensions.split(",")]
    
    log.info("=" * 80)
    log.info("Foundry IQ Knowledge Base Bootstrap")
    log.info("=" * 80)
    log.info(f"KB Name:       {args.kb_name}")
    log.info(f"KB Desc:       {args.kb_desc}")
    log.info(f"Doc Dir:       {doc_dir}")
    log.info(f"Extensions:    {extensions}")
    log.info("=" * 80)
    
    try:
        kb_id = bootstrap_knowledge_base(
            kb_display_name=args.kb_name,
            kb_description=args.kb_desc,
            document_dir=str(doc_dir),
            file_extensions=extensions
        )
        
        log.info("=" * 80)
        log.info(f"✓ SUCCESS! Knowledge Base ID: {kb_id}")
        log.info("=" * 80)
        log.info("\nNext steps:")
        log.info(f"  1. Copy the KB ID: {kb_id}")
        log.info("  2. Update agents/shared/fabric_agent.py:")
        log.info(f'     kb_tool = RetrievalAugmentedGenerationTool(knowledge_base_id="{kb_id}", ...)')
        log.info("  3. Run: python -m agents.server")
        log.info("  4. Test in DevUI with a KB-related question")
        log.info("")
        
        return 0
        
    except Exception as exc:
        log.exception("Failed to bootstrap knowledge base")
        return 1


if __name__ == "__main__":
    sys.exit(main())
