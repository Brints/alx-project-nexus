from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from django.utils import timezone

from .models import Poll, PollCategory
from .serializers import PollCreateSerializer, PollListSerializer, PollCategorySerializer, VoteSerializer
from .permissions import IsPollCreatorOrOrgAdmin
from organizations.models import OrganizationMember


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PollCategory.objects.all()
    serializer_class = PollCategorySerializer
    permission_classes = [permissions.AllowAny]


class PollViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, IsPollCreatorOrOrgAdmin]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['question', 'category__name']
    ordering_fields = ['created_at', 'end_date']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return PollCreateSerializer
        return PollListSerializer

    def get_queryset(self):
        """
        Filter polls visibility:
        1. Polls created by the user.
        2. Public polls.
        3. Private Organization polls WHERE user is a member.
        """
        user = self.request.user

        # Get IDs of organizations the user belongs to
        user_org_ids = OrganizationMember.objects.filter(user=user).values_list('organization_id', flat=True)

        return Poll.objects.filter(
            Q(creator=user) |
            Q(is_public=True) |
            Q(organization__id__in=user_org_ids)
        ).distinct().select_related('category', 'creator', 'organization')

    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """
        Manual override to close a poll before expiry.
        Only Creator or Org Admin can do this (handled by permission class).
        """
        poll = self.get_object()

        if not poll.is_active:
            return Response({"message": "Poll is already closed."}, status=status.HTTP_400_BAD_REQUEST)

        poll.is_active = False
        poll.end_date = timezone.now()  # Update end date to now
        poll.save()

        return Response({"message": "Poll closed successfully."}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[permissions.AllowAny])
    def vote(self, request, pk=None):
        """
        Endpoint: POST /api/polls/{id}/vote/
        Body: { "option_id": 1 }
        """
        poll = self.get_object()

        serializer = VoteSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)

        # Ensure the option belongs to the poll in the URL
        if serializer.validated_data['option'].poll != poll:
            return Response(
                {"error": "Invalid option for this poll."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer.save()

        return Response(
            {"message": "Vote cast successfully."},
            status=status.HTTP_201_CREATED
        )