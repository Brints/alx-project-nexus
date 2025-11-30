from rest_framework import viewsets, status, permissions, filters, serializers
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from django.db.models import Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema

from .models import Poll, PollCategory, PollOption, Vote
from .permissions import CanCreateCategory, IsPollCreatorOrOrgAdmin
from .serializers import (
    PollCreateSerializer,
    PollListSerializer,
    PollCategorySerializer,
    VoteSerializer,
)
from organizations.models import OrganizationMember
from .utils import get_client_ip, get_country_from_ip


@extend_schema(tags=["Categories"])
class CategoryViewSet(viewsets.ModelViewSet):
    queryset = PollCategory.objects.all()
    serializer_class = PollCategorySerializer
    lookup_field = "category_id"

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [permissions.IsAuthenticated(), CanCreateCategory()]
        return [permissions.AllowAny()]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


@extend_schema(tags=["Polls"])
class PollViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, IsPollCreatorOrOrgAdmin]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["poll_question", "poll_category__name"]
    ordering_fields = ["created_at", "end_date"]
    lookup_field = "poll_id"

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return PollCreateSerializer
        return PollListSerializer

    def get_queryset(self):
        """
        Filter polls visibility:
        1. Polls created by the user.
        2. Public polls.
        3. Private Organization polls WHERE user is a member.
        Exception: For 'vote' action, return all active polls (validation happens in serializer).
        """
        user = self.request.user

        # For vote action, return all polls (permission check in serializer)
        if self.action == "vote":
            return Poll.objects.all().select_related(
                "poll_category", "creator", "organization"
            )

        # Anonymous users only see public polls
        if user.is_anonymous:
            return Poll.objects.filter(is_public=True)

        # Get the Organization IDs where the user is a member
        user_org_ids = OrganizationMember.objects.filter(user=user).values_list(
            "organization", flat=True
        )

        return (
            Poll.objects.filter(
                Q(creator=user) | Q(is_public=True) | Q(organization__in=user_org_ids)
            )
            .distinct()
            .select_related("poll_category", "creator", "organization")
        )

    def perform_create(self, serializer):
        """
        Inject the current user as the 'creator' of the poll.
        This passes 'creator=request.user' to the serializer's create() method.
        """
        serializer.save(creator=self.request.user)

    @extend_schema(
        summary="Manually Close a Poll",
        request=None,
        responses={200: {"description": "Poll closed successfully"}},
    )
    @action(detail=True, methods=["post"])
    def close(self, request, poll_id=None):
        """
        Manual override to close a poll before expiry.
        - Organization polls: Only Org Admins can close
        - Personal/Public polls: Only the creator can close
        """
        poll = self.get_object()

        if not poll.is_active:
            return Response(
                {"message": "Poll is already closed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user

        # Check permissions based on poll type
        if poll.organization:
            # Organization poll - must be admin
            is_admin = OrganizationMember.objects.filter(
                organization=poll.organization,
                user=user,
                role=OrganizationMember.Role.ADMIN,
            ).exists()

            if not is_admin:
                return Response(
                    {"error": "Only organization admins can close this poll."},
                    status=status.HTTP_403_FORBIDDEN,
                )
        else:
            # Personal/Public poll - must be creator
            if poll.creator != user:
                return Response(
                    {"error": "Only the poll creator can close this poll."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        poll.is_active = False
        poll.manually_closed = True
        poll.end_date = timezone.now()
        poll.save()

        return Response(
            {"message": "Poll closed successfully."}, status=status.HTTP_200_OK
        )

    @extend_schema(
        summary="Cast a Vote",
        request=VoteSerializer,
        responses={201: {"description": "Vote cast successfully"}},
    )
    @action(detail=True, methods=["post"], permission_classes=[permissions.AllowAny])
    def vote(self, request, poll_id=None):
        """
        Vote on a poll.
        Anonymous users can vote on Public polls (tracked by IP).
        Authenticated users are tracked by User ID.
        """
        # This calls get_object(), which calls get_queryset() (where the error was)
        poll = self.get_object()

        if isinstance(request.data, dict):
            data = request.data.copy()
        else:
            data = dict(request.data)

        data["poll_id"] = poll.poll_id

        # Pass context to serializer so it can check duplicates
        serializer = VoteSerializer(data=data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        # Ensure the option belongs to the poll in the URL
        if serializer.validated_data["option"].poll != poll:
            return Response(
                {"error": "Invalid option for this poll."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer.save()

        return Response(
            {"message": "Vote cast successfully."}, status=status.HTTP_201_CREATED
        )
