import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from prism.api.dependencies import (
    gap_analyzer,
    path_generator,
    rec_engine,
    skill_graph,
    skill_repo,
    skill_tracker,
)
from prism.intelligence.models.skill_models import (
    DeveloperSkill,
    DeveloperSkillProfile,
    SkillEvidence,
    SkillGraphData,
    SkillNode,
)
from prism.learning.models import (
    KnowledgeGap,
    LearningPath,
    LearningRecommendation,
)
from prism.logging.logger import get_logger
from prism.security import get_optional_current_user, verify_developer_ownership

logger = get_logger(__name__)

router = APIRouter(prefix="/skills", tags=["Skills & Intelligence"])


# =========================================================================
# REQUEST & RESPONSE MODELS
# =========================================================================


class RecordEvidenceAPIRequest(BaseModel):
    developer_id: str = Field(min_length=1, description="Unique developer identifier")
    skill_name: str = Field(min_length=1, description="Name of the technical skill")
    skill_id: str | None = Field(
        default=None, description="Optional canonical skill identifier"
    )
    evidence_type: str = Field(
        default="implementation",
        description="Evidence category (e.g. implementation, test_execution)",
    )
    description: str = Field(
        min_length=1, description="Verifiable activity description"
    )
    project_path: str | None = Field(
        default=None, description="Repository or project path"
    )
    programming_language: str | None = Field(
        default=None, description="Associated programming language"
    )
    framework: str | None = Field(
        default=None, description="Associated library or framework"
    )
    evidence_source: str = Field(
        default="direct", description="Source of evidence (direct, activity_stream)"
    )
    evidence_strength: float = Field(
        default=1.0, ge=0.0, le=5.0, description="Evidence impact weight"
    )
    confidence_score: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Confidence in observation"
    )
    complexity_score: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Implementation complexity"
    )
    related_activity_id: str | None = Field(
        default=None, description="Correlated developer activity event ID"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional structured attributes"
    )


class SkillGapAnalysisRequest(BaseModel):
    developer_id: str = Field(min_length=1, description="Target developer ID")
    target_goal: str | None = Field(
        default=None, description="Target skill goal (e.g. 'FastAPI')"
    )
    target_skill: str | None = Field(default=None, description="Alias for target_goal")
    target_role: str | None = Field(
        default=None,
        description="Target career role (e.g. 'Machine Learning Engineer')",
    )


class SkillLearningPathRequest(BaseModel):
    developer_id: str = Field(min_length=1, description="Target developer ID")
    target_goal: str | None = Field(default=None, description="Target skill goal")
    target_role: str | None = Field(default=None, description="Target career role")


# =========================================================================
# DEVELOPER SKILL PROFILE & EVIDENCE ENDPOINTS
# =========================================================================


@router.get(
    "/profile/{developer_id}",
    response_model=DeveloperSkillProfile,
    status_code=status.HTTP_200_OK,
)
async def get_developer_skill_profile(
    developer_id: str,
    current_user: Any = Depends(get_optional_current_user),
) -> DeveloperSkillProfile:
    """Retrieve complete multidimensional skill profile for a developer."""
    cleaned_id = developer_id.strip()
    if not cleaned_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Developer ID cannot be empty",
        )
    verify_developer_ownership(cleaned_id, current_user)
    try:
        logger.info("API request: fetch skill profile | dev=%s", cleaned_id)
        return skill_tracker.get_profile(cleaned_id)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)
        ) from err
    except Exception as err:
        logger.exception("Failed to retrieve skill profile")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve skill profile",
        ) from err


@router.post(
    "/evidence",
    response_model=DeveloperSkill,
    status_code=status.HTTP_201_CREATED,
)
async def record_skill_evidence(
    request: RecordEvidenceAPIRequest,
    current_user: Any = Depends(get_optional_current_user),
) -> DeveloperSkill:
    """Record verifiable evidence for a skill and re-evaluate developer proficiency."""
    verify_developer_ownership(request.developer_id.strip(), current_user)
    try:
        now = datetime.now(UTC)
        canonical_skill_id = (
            request.skill_id or request.skill_name.strip().lower().replace(" ", "_")
        )
        evidence = SkillEvidence(
            evidence_id=f"ev_{uuid.uuid4().hex[:12]}",
            developer_id=request.developer_id.strip(),
            skill_name=request.skill_name.strip(),
            skill_id=canonical_skill_id,
            evidence_type=request.evidence_type.strip(),
            description=request.description.strip(),
            project_path=request.project_path,
            programming_language=request.programming_language,
            framework=request.framework,
            evidence_source=request.evidence_source,
            evidence_strength=request.evidence_strength,
            confidence_score=request.confidence_score,
            complexity_score=request.complexity_score,
            timestamp=now,
            related_activity_id=request.related_activity_id,
            metadata=dict(request.metadata),
        )

        logger.info(
            "API request: record skill evidence | dev=%s | skill=%s | type=%s",
            evidence.developer_id,
            evidence.skill_name,
            evidence.evidence_type,
        )
        return skill_tracker.record_evidence(evidence)

    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)
        ) from err
    except Exception as err:
        logger.exception("Failed to record skill evidence")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record skill evidence",
        ) from err


@router.get(
    "/evidence/{developer_id}",
    response_model=list[SkillEvidence],
    status_code=status.HTTP_200_OK,
)
async def get_developer_evidence(
    developer_id: str,
    skill_name: str | None = Query(
        default=None, description="Optional skill name filter"
    ),
    limit: int = Query(
        default=50, ge=1, le=500, description="Maximum evidence items to return"
    ),
    offset: int = Query(default=0, ge=0, description="Items to skip"),
    current_user: Any = Depends(get_optional_current_user),
) -> list[SkillEvidence]:
    """Retrieve chronological skill evidence records for a developer."""
    cleaned_id = developer_id.strip()
    if not cleaned_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Developer ID cannot be empty",
        )
    verify_developer_ownership(cleaned_id, current_user)

    try:
        all_evidence = skill_repo.get_evidence(cleaned_id, skill_name=skill_name)
        # If repository returned empty, check in-memory tracker profile as fallback
        if not all_evidence:
            profile = skill_tracker.get_profile(cleaned_id)
            if skill_name:
                s_key = skill_name.strip().lower()
                dev_skill = profile.skills.get(s_key)
                all_evidence = list(dev_skill.evidence_list) if dev_skill else []
            else:
                collected: list[SkillEvidence] = []
                for s in profile.skills.values():
                    collected.extend(s.evidence_list)
                collected.sort(key=lambda e: e.timestamp)
                all_evidence = collected

        return all_evidence[offset : offset + limit]

    except Exception as err:
        logger.exception("Failed to retrieve skill evidence")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve skill evidence",
        ) from err


# =========================================================================
# SKILL PROFICIENCY ENDPOINTS
# =========================================================================


@router.get(
    "/proficiency/{developer_id}",
    response_model=dict[str, DeveloperSkill],
    status_code=status.HTTP_200_OK,
)
async def get_developer_proficiencies(
    developer_id: str,
    current_user: Any = Depends(get_optional_current_user),
) -> dict[str, DeveloperSkill]:
    """Retrieve all assessed skill proficiencies for a developer."""
    cleaned_id = developer_id.strip()
    if not cleaned_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Developer ID cannot be empty",
        )
    verify_developer_ownership(cleaned_id, current_user)
    profile = skill_tracker.get_profile(cleaned_id)
    return profile.skills


@router.get(
    "/proficiency/{developer_id}/{skill_id}",
    response_model=DeveloperSkill,
    status_code=status.HTTP_200_OK,
)
async def get_single_skill_proficiency(
    developer_id: str,
    skill_id: str,
    current_user: Any = Depends(get_optional_current_user),
) -> DeveloperSkill:
    """Retrieve current assessed proficiency and reasoning for a single skill."""
    cleaned_id = developer_id.strip()
    cleaned_skill = skill_id.strip()
    if not cleaned_id or not cleaned_skill:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Developer ID and Skill ID must be non-empty",
        )
    verify_developer_ownership(cleaned_id, current_user)

    # Resolve canonical name from graph if available
    node = skill_graph.get_node(cleaned_skill)
    lookup_name = node.name if node else cleaned_skill
    return skill_tracker.assess_skill(cleaned_id, lookup_name)


# =========================================================================
# SKILL GRAPH ENDPOINTS
# =========================================================================


@router.get(
    "/graph",
    response_model=SkillGraphData,
    status_code=status.HTTP_200_OK,
)
async def get_skill_graph_snapshot(
    category: str | None = Query(default=None, description="Filter skills by category"),
    language: str | None = Query(default=None, description="Filter skills by language"),
) -> SkillGraphData:
    """Retrieve technical skill graph topology with optional category/language filters."""
    graph_data = skill_graph.export_graph()

    if category:
        cat_lower = category.lower().strip()
        filtered_names = set(skill_graph.filter_by_category(cat_lower))
        filtered_nodes = [
            n for n in graph_data.nodes if n.category.lower() == cat_lower
        ]
        filtered_skills = [s for s in graph_data.skills if s in filtered_names]
        filtered_rels = [
            r
            for r in graph_data.relationships
            if r.from_skill in filtered_names or r.to_skill in filtered_names
        ]
        return SkillGraphData(
            skills=filtered_skills,
            nodes=filtered_nodes,
            relationships=filtered_rels,
        )

    if language:
        lang_lower = language.lower().strip()
        filtered_names = set(skill_graph.filter_by_language(lang_lower))
        filtered_nodes = [
            n for n in graph_data.nodes if (n.language or "").lower() == lang_lower
        ]
        filtered_skills = [s for s in graph_data.skills if s in filtered_names]
        filtered_rels = [
            r
            for r in graph_data.relationships
            if r.from_skill in filtered_names or r.to_skill in filtered_names
        ]
        return SkillGraphData(
            skills=filtered_skills,
            nodes=filtered_nodes,
            relationships=filtered_rels,
        )

    return graph_data


@router.get(
    "/graph/{skill_id}",
    response_model=SkillNode,
    status_code=status.HTTP_200_OK,
)
async def get_skill_node(skill_id: str) -> SkillNode:
    """Retrieve detailed node metadata for a skill in the graph."""
    cleaned = skill_id.strip()
    node = skill_graph.get_node(cleaned)
    if node is not None:
        return node

    # Check if skill name exists in raw graph skills
    for s in skill_graph.get_skills():
        if s.lower() == cleaned.lower():
            return skill_graph._ensure_node(s)

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Skill '{cleaned}' not found in skill graph",
    )


@router.get(
    "/prerequisites/{skill_id}",
    response_model=list[str],
    status_code=status.HTTP_200_OK,
)
async def get_skill_prerequisites(
    skill_id: str,
    transitive: bool = Query(
        default=False, description="Include transitive indirect prerequisites"
    ),
) -> list[str]:
    """Retrieve prerequisite skills required for a given technical skill."""
    cleaned = skill_id.strip()
    node = skill_graph.get_node(cleaned)
    canonical_name = node.name if node else cleaned

    # Check if skill exists in graph
    if canonical_name not in skill_graph.get_skills() and not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill '{cleaned}' not found in skill graph",
        )

    return skill_graph.get_prerequisites(canonical_name, transitive=transitive)


@router.get(
    "/related/{skill_id}",
    response_model=list[str],
    status_code=status.HTTP_200_OK,
)
async def get_related_skills(skill_id: str) -> list[str]:
    """Retrieve related or adjacent skills for a given technical skill."""
    cleaned = skill_id.strip()
    node = skill_graph.get_node(cleaned)
    canonical_name = node.name if node else cleaned

    if canonical_name not in skill_graph.get_skills() and not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill '{cleaned}' not found in skill graph",
        )

    return skill_graph.get_related(canonical_name)


# =========================================================================
# SKILL GAP ANALYSIS & RECOMMENDATIONS ENDPOINTS
# =========================================================================


@router.post(
    "/gap-analysis",
    response_model=list[KnowledgeGap],
    status_code=status.HTTP_200_OK,
)
async def perform_gap_analysis(
    request: SkillGapAnalysisRequest,
    current_user: Any = Depends(get_optional_current_user),
) -> list[KnowledgeGap]:
    """Analyze developer proficiencies to identify missing prerequisites and concept gaps."""
    cleaned_id = request.developer_id.strip()
    verify_developer_ownership(cleaned_id, current_user)
    target_goal = (request.target_goal or request.target_skill or "").strip()
    target_role = (request.target_role or "").strip()

    if not target_goal and not target_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must specify at least one of target_goal, target_skill, or target_role",
        )

    profile = skill_tracker.get_profile(cleaned_id)

    try:
        if target_role:
            return gap_analyzer.identify_role_gaps(profile, target_role)
        return gap_analyzer.identify_gaps(profile, target_goal)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)
        ) from err


@router.get(
    "/gaps/{developer_id}",
    response_model=list[KnowledgeGap],
    status_code=status.HTTP_200_OK,
)
async def get_developer_gaps(
    developer_id: str,
    target_goal: str | None = Query(default=None, description="Optional target skill"),
    target_role: str | None = Query(
        default=None, description="Optional target career role"
    ),
    current_user: Any = Depends(get_optional_current_user),
) -> list[KnowledgeGap]:
    """Fetch current detected knowledge gaps for a developer."""
    cleaned_id = developer_id.strip()
    if not cleaned_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Developer ID cannot be empty",
        )
    verify_developer_ownership(cleaned_id, current_user)

    profile = skill_tracker.get_profile(cleaned_id)

    try:
        if target_role:
            return gap_analyzer.identify_role_gaps(profile, target_role.strip())
        if target_goal:
            return gap_analyzer.identify_gaps(profile, target_goal.strip())

        # If neither specified, aggregate gaps across all developer's registered skills
        all_gaps: list[KnowledgeGap] = []
        for s in profile.skills.values():
            all_gaps.extend(gap_analyzer.identify_gaps(profile, s.skill_name))
        return all_gaps

    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)
        ) from err


@router.get(
    "/recommendations/{developer_id}",
    response_model=list[LearningRecommendation],
    status_code=status.HTTP_200_OK,
)
async def get_developer_recommendations(
    developer_id: str,
    target_goal: str | None = Query(default=None, description="Optional target skill"),
    target_role: str | None = Query(
        default=None, description="Optional target career role"
    ),
    current_user: Any = Depends(get_optional_current_user),
) -> list[LearningRecommendation]:
    """Generate prioritized, structured learning recommendations for a developer."""
    cleaned_id = developer_id.strip()
    if not cleaned_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Developer ID cannot be empty",
        )
    verify_developer_ownership(cleaned_id, current_user)

    profile = skill_tracker.get_profile(cleaned_id)

    try:
        if target_role:
            gaps = gap_analyzer.identify_role_gaps(profile, target_role.strip())
            return rec_engine.generate_recommendations(
                profile, gaps, target_role=target_role.strip()
            )

        if target_goal:
            gaps = gap_analyzer.identify_gaps(profile, target_goal.strip())
            return rec_engine.generate_recommendations(profile, gaps, target_role=None)

        # Default: analyze across recorded skills
        gaps = []
        for s in profile.skills.values():
            gaps.extend(gap_analyzer.identify_gaps(profile, s.skill_name))
        return rec_engine.generate_recommendations(profile, gaps)

    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)
        ) from err


# =========================================================================
# LEARNING PATH ENDPOINTS
# =========================================================================


@router.post(
    "/learning-path",
    response_model=LearningPath,
    status_code=status.HTTP_200_OK,
)
async def create_learning_path(
    request: SkillLearningPathRequest,
    current_user: Any = Depends(get_optional_current_user),
) -> LearningPath:
    """Generate an ordered, prerequisite-respecting learning path for a skill or role."""
    cleaned_id = request.developer_id.strip()
    verify_developer_ownership(cleaned_id, current_user)
    target_goal = (request.target_goal or "").strip()
    target_role = (request.target_role or "").strip()

    if not target_goal and not target_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must specify target_goal or target_role",
        )

    profile = skill_tracker.get_profile(cleaned_id)

    try:
        if target_role:
            return path_generator.generate_role_path(profile, target_role)
        return path_generator.generate_path(profile, target_goal)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)
        ) from err


@router.get(
    "/learning-path/{developer_id}",
    response_model=LearningPath,
    status_code=status.HTTP_200_OK,
)
async def get_developer_learning_path(
    developer_id: str,
    target_goal: str | None = Query(default=None, description="Target skill goal"),
    target_role: str | None = Query(default=None, description="Target career role"),
    current_user: Any = Depends(get_optional_current_user),
) -> LearningPath:
    """Fetch an ordered learning path for a developer toward a target goal or role."""
    cleaned_id = developer_id.strip()
    if not cleaned_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Developer ID cannot be empty",
        )
    verify_developer_ownership(cleaned_id, current_user)

    if not target_goal and not target_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either target_goal or target_role must be provided",
        )

    profile = skill_tracker.get_profile(cleaned_id)

    try:
        if target_role:
            return path_generator.generate_role_path(profile, target_role.strip())
        assert target_goal is not None
        return path_generator.generate_path(profile, target_goal.strip())
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)
        ) from err
