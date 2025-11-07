"""
Parameter Extraction Utilities

Contains all parameter extraction methods for parsing structured data
from natural language queries.
"""

import re
from typing import Dict, List, Optional, Tuple
from .app_config import (
    STATUS_MAPPINGS, INSTRUCTION_KEYWORDS, QUANTITY_PATTERNS,
    NAME_PATTERNS, STATUS_PATTERNS, TARGET_DATE_PATTERNS,
    PRIORITY_PATTERNS, DESCRIPTION_PATTERNS
)


class ParameterExtractor:
    """Utility class for extracting structured parameters from natural language queries"""
    
    @staticmethod
    def normalize_status_value(value: str) -> str:
        """Normalize status/progress strings into a user-facing label."""
        clean = str(value).strip()
        clean = clean.replace('-', ' ').replace('_', ' ')
        clean = re.sub(r'\s+', ' ', clean)
        
        lower = clean.lower()
        if lower in STATUS_MAPPINGS:
            return STATUS_MAPPINGS[lower]
        return clean.title()

    @staticmethod
    def clean_value_phrase(text: str) -> str:
        """Clean value phrases by removing connecting words"""
        snippet = (text or "").strip()
        if not snippet:
            return snippet
        snippet = re.split(r"\b(?:and|also|then|so|but)\b", snippet, maxsplit=1, flags=re.IGNORECASE)[0]
        return snippet.strip()

    @staticmethod
    def extract_additional_parameters(query: str) -> Dict:
        """
        Extract structured fields from query text (status, dates, priority, etc.).
        """
        params: Dict[str, str] = {}
        
        # Status / workflow field changes
        for pattern in STATUS_PATTERNS:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                status_raw = ParameterExtractor.clean_value_phrase(match.group(1))
                params["status"] = ParameterExtractor.normalize_status_value(status_raw)
                break

        # Target/Due date extraction
        for pattern in TARGET_DATE_PATTERNS:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                target_raw = ParameterExtractor.clean_value_phrase(match.group(1)).rstrip('.')
                params["target_date"] = target_raw.title()
                break
        
        # Priority changes
        for pattern in PRIORITY_PATTERNS:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                priority_raw = ParameterExtractor.clean_value_phrase(match.group(1))
                params["priority"] = priority_raw.title()
                break

        # Description instructions
        for pattern in DESCRIPTION_PATTERNS:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                params["description"] = ParameterExtractor.clean_value_phrase(match.group(1)).rstrip(".")
                break
        
        return params

    @staticmethod
    def extract_quantity_and_names(query: str, obj: str) -> Tuple[int, List[str], bool]:
        """
        Extract quantity and names from query for multi-task detection
        
        Returns:
            Tuple of (count, extracted_names, is_multi_task)
        """
        count = 1
        extracted_names = []
        is_multi_task = False
        
        # Check for quantity patterns (multi-task detection)
        for pattern_template in QUANTITY_PATTERNS:
            pattern = pattern_template.format(obj=obj)
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                count = int(match.group(1))
                if count > 1:
                    is_multi_task = True
                break
        
        # Try to extract name patterns
        for pattern in NAME_PATTERNS:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                extracted_text = match.group(1).strip()
                
                # Process the extracted text for names and instructions
                name_candidate, instruction_tail = ParameterExtractor._split_names_from_instructions(extracted_text)
                
                # Check if it's a series (contains commas OR multiple distinct parts)
                if ',' in name_candidate:
                    parts = [part.strip() for part in name_candidate.split(',') if part.strip()]
                else:
                    parts = [name_candidate]
                
                # Filter out parts that look like instructions
                cleaned_parts = ParameterExtractor._filter_instruction_keywords(parts)
                
                if cleaned_parts:
                    if len(cleaned_parts) > 1:
                        is_multi_task = True
                        extracted_names = cleaned_parts
                        count = len(cleaned_parts)
                    else:
                        extracted_names = [cleaned_parts[0].strip().strip(" '\"")]
                break
        
        return count, extracted_names, is_multi_task

    @staticmethod
    def _split_names_from_instructions(text: str) -> Tuple[str, str]:
        """Split name candidates from instruction text"""
        def split_instruction(text: str):
            lower = text.lower()
            for kw in INSTRUCTION_KEYWORDS:
                idx = lower.find(kw + " ")
                if idx != -1:
                    return text[:idx].strip(), text[idx:].strip()
            return text.strip(), ""

        # If there's an " and " that likely separates instructions, split once
        if " and " in text.lower():
            split_parts = re.split(r'\s+and\s+', text, maxsplit=1, flags=re.IGNORECASE)
            name_candidate = split_parts[0].strip()
            instruction_tail = split_parts[1].strip() if len(split_parts) > 1 else ""
        else:
            name_candidate = text
            instruction_tail = ""

        # Remove instruction phrases embedded in the candidate
        name_candidate, embedded_tail = split_instruction(name_candidate)
        if embedded_tail:
            instruction_tail = f"{embedded_tail} {'and ' + instruction_tail if instruction_tail else ''}".strip()

        return name_candidate, instruction_tail

    @staticmethod
    def _filter_instruction_keywords(parts: List[str]) -> List[str]:
        """Filter out parts that look like instructions"""
        cleaned_parts = []
        for part in parts:
            part_lower = part.lower()
            if any(part_lower.startswith(k) for k in INSTRUCTION_KEYWORDS):
                continue
            cleaned_parts.append(part)
        return cleaned_parts

    @staticmethod
    def extract_names_by_object_type(names: List[str], obj: str) -> Dict[str, str]:
        """Extract names and map them to appropriate parameter keys based on object type"""
        if not names:
            return {}
        
        if len(names) == 1:
            single_name = names[0]
            if obj == "project":
                return {"project_name": single_name}
            elif obj == "page":
                return {"page_name": single_name}
            elif obj == "database":
                return {"database_name": single_name}
            elif obj == "issue":
                return {"issue_title": single_name}
            else:
                return {"name": single_name}
        else:
            return {"names": names, "count": len(names)}

    @staticmethod
    def generate_name_pattern_if_needed(query: str, obj: str, count: int, has_names: bool) -> Optional[str]:
        """Generate name pattern for numbered series if detected"""
        if has_names or count <= 1:
            return None
        
        # Try to detect pattern like "Bug 1 through 5" or "assignment 1, 2, 3"
        if "through" in query or "to" in query:
            # Generate numbered series pattern
            base_name = obj.title()  # Default base name
            return f"{base_name} {{i}}"
        
        return None

    @staticmethod
    def merge_parameters(llm_params: Dict, heuristic_params: Dict) -> Dict:
        """Merge LLM-extracted parameters with heuristic parameters"""
        params = dict(llm_params) if llm_params else {}
        heuristic_params = heuristic_params if heuristic_params else {}
        
        # Merge individual name parameters if missing
        for key in ["project_name", "page_name", "database_name", "issue_title", "name", "name_pattern"]:
            if key not in params and heuristic_params.get(key):
                params[key] = heuristic_params[key]
        
        # Merge explicit lists of names
        if heuristic_params.get("names"):
            if not params.get("names"):
                params["names"] = heuristic_params["names"]
            else:
                # Ensure uniqueness while preserving order
                existing = params["names"]
                for name in heuristic_params["names"]:
                    if name not in existing:
                        existing.append(name)
                params["names"] = existing
        
        # Clean name lists to remove instruction-like entries
        if params.get("names"):
            cleaned_names = []
            for name in params["names"]:
                lower_name = name.lower().strip()
                if any(lower_name.startswith(k) for k in INSTRUCTION_KEYWORDS):
                    continue
                cleaned_names.append(name)
            if cleaned_names:
                params["names"] = cleaned_names
            else:
                params.pop("names", None)
                params.pop("count", None)
        
        # Merge counts
        if "count" not in params and heuristic_params.get("count"):
            params["count"] = heuristic_params["count"]
        
        # If we have names but no count, infer it
        if params.get("names") and not params.get("count"):
            params["count"] = len(params["names"])
        
        return params

    @staticmethod
    def normalize_parameter_synonyms(params: Dict) -> Dict:
        """Normalize synonymous parameter fields"""
        # Normalize synonymous fields
        if "status" not in params and "progress" in params:
            progress_val = params.pop("progress")
            params["status"] = ParameterExtractor.normalize_status_value(progress_val) if isinstance(progress_val, str) else progress_val
        
        if "backlog_progress" in params:
            backlog_val = params.pop("backlog_progress")
            params["status"] = ParameterExtractor.normalize_status_value(backlog_val)
        
        if "backlog_modal" in params:
            backlog_val = params.pop("backlog_modal")
            params["status"] = ParameterExtractor.normalize_status_value(backlog_val)
        
        if "status" in params and isinstance(params["status"], str):
            params["status"] = ParameterExtractor.normalize_status_value(params["status"])
        
        if "target_date" in params and isinstance(params["target_date"], str):
            params["target_date"] = params["target_date"].strip().rstrip(".")

        return params

    @staticmethod
    def determine_multi_task_flag(params: Dict, heuristic_multi: bool = False) -> bool:
        """Determine if this should be treated as a multi-task"""
        is_multi = False
        
        if params.get("names"):
            is_multi = len(params["names"]) > 1
            if not is_multi:
                params.pop("names", None)
        
        if params.get("count", 1) > 1:
            is_multi = True
        
        if heuristic_multi:
            is_multi = True
        
        if not params.get("names") and params.get("count", 1) <= 1:
            params.pop("count", None)
        
        return is_multi