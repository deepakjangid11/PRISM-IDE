"""Code and document text chunking with AST awareness and line mapping (Phase 20)."""

import ast
import uuid
from pathlib import Path

from prism.logging.logger import get_logger
from prism.rag.schemas import DocumentChunk

logger = get_logger(__name__)


class CodeDocumentChunker:
    """Chunks source code and documentation into semantically bounded fragments."""

    def __init__(
        self,
        default_chunk_size: int = 500,
        default_chunk_overlap: int = 100,
    ) -> None:
        self.chunk_size = default_chunk_size
        self.chunk_overlap = default_chunk_overlap

    def chunk_file(
        self,
        file_path: str,
        content: str,
    ) -> list[DocumentChunk]:
        """Extract chunks tailored to the file format."""
        suffix = Path(file_path).suffix.lower()

        if suffix == ".py":
            return self._chunk_python_file(file_path, content)
        if suffix in (".md", ".markdown", ".txt"):
            return self._chunk_text_file(file_path, content, chunk_type="markdown")
        return self._chunk_line_blocks(file_path, content, chunk_type="code")

    def _chunk_python_file(
        self,
        file_path: str,
        content: str,
    ) -> list[DocumentChunk]:
        """AST-aware chunker extracting classes, functions, and module docstring."""
        chunks: list[DocumentChunk] = []
        lines = content.splitlines()

        try:
            tree = ast.parse(content, filename=file_path)

            # 1. Module docstring
            docstring = ast.get_docstring(tree)
            if docstring:
                chunks.append(
                    DocumentChunk(
                        chunk_id=f"chk_{uuid.uuid4().hex[:10]}",
                        file_path=file_path,
                        content=docstring.strip(),
                        start_line=1,
                        end_line=len(docstring.splitlines()),
                        chunk_type="docstring",
                        language="python",
                        metadata={"type": "module_docstring"},
                    )
                )

            # 2. Top-level classes and functions
            for node in tree.body:
                if isinstance(
                    node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
                ):
                    start_line = node.lineno
                    end_line = getattr(node, "end_lineno", start_line) or start_line
                    block_content = "\n".join(lines[start_line - 1 : end_line])

                    kind = "class" if isinstance(node, ast.ClassDef) else "function"
                    chunks.append(
                        DocumentChunk(
                            chunk_id=f"chk_{uuid.uuid4().hex[:10]}",
                            file_path=file_path,
                            content=block_content.strip(),
                            start_line=start_line,
                            end_line=end_line,
                            chunk_type="code",
                            language="python",
                            metadata={"name": node.name, "kind": kind},
                        )
                    )

            if chunks:
                return chunks
        except (SyntaxError, ValueError, TypeError, AttributeError, OSError) as e:
            logger.debug(
                "AST parsing failed for %s, falling back to line chunking: %s",
                file_path,
                e,
            )

        # Fallback to sliding window line chunks
        return self._chunk_line_blocks(
            file_path, content, chunk_type="code", language="python"
        )

    def _chunk_text_file(
        self,
        file_path: str,
        content: str,
        chunk_type: str = "markdown",
    ) -> list[DocumentChunk]:
        """Chunk markdown or prose text into paragraphs or sliding windows."""
        paragraphs = content.split("\n\n")
        chunks: list[DocumentChunk] = []
        current_line = 1

        for para in paragraphs:
            text = para.strip()
            line_count = len(text.splitlines())
            if text:
                chunks.append(
                    DocumentChunk(
                        chunk_id=f"chk_{uuid.uuid4().hex[:10]}",
                        file_path=file_path,
                        content=text,
                        start_line=current_line,
                        end_line=current_line + line_count - 1,
                        chunk_type=chunk_type,
                        language=Path(file_path).suffix.lstrip("."),
                        metadata={},
                    )
                )
            current_line += line_count + 1

        return chunks or self._chunk_line_blocks(
            file_path, content, chunk_type=chunk_type
        )

    def _chunk_line_blocks(
        self,
        file_path: str,
        content: str,
        chunk_type: str = "code",
        language: str | None = None,
    ) -> list[DocumentChunk]:
        """Sliding line window chunker for general source files."""
        lines = content.splitlines()
        chunks: list[DocumentChunk] = []
        if not lines:
            return chunks

        step = max(1, self.chunk_size - self.chunk_overlap)
        total_lines = len(lines)

        for i in range(0, total_lines, step):
            window_lines = lines[i : i + self.chunk_size]
            if not window_lines:
                continue

            block = "\n".join(window_lines).strip()
            if block:
                chunks.append(
                    DocumentChunk(
                        chunk_id=f"chk_{uuid.uuid4().hex[:10]}",
                        file_path=file_path,
                        content=block,
                        start_line=i + 1,
                        end_line=min(total_lines, i + len(window_lines)),
                        chunk_type=chunk_type,
                        language=language or Path(file_path).suffix.lstrip("."),
                        metadata={},
                    )
                )

        return chunks
