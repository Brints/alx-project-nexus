from django.shortcuts import get_object_or_404
from rest_framework import serializers
from django.utils import timezone
from django.db import transaction
from .models import Poll, PollCategory, PollOption, Vote
from organizations.models import Organization, OrganizationMember
from .utils import get_client_ip, get_country_from_ip


class PollCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PollCategory
        fields = ['id', 'name']


class PollOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PollOption
        fields = ['id', 'text', 'image', 'vote_count']
        read_only_fields = ['vote_count']


class PollCreateSerializer(serializers.ModelSerializer):
    options = PollOptionSerializer(many=True)
    organization_id = serializers.UUIDField(required=False, allow_null=True, write_only=True)

    class Meta:
        model = Poll
        fields = [
            'poll_id', 'poll_question', 'poll_category', 'options',
            'start_date', 'end_date', 'is_public',
            'allowed_country', 'organization_id'
        ]

    def validate(self, attrs):
        user = self.context['request'].user
        org_id = attrs.get('organization_id')

        # --- Organization Permission Check ---
        if org_id:
            try:
                org = Organization.objects.get(pk=org_id)
                # Check if user is ADMIN of this org
                is_admin = OrganizationMember.objects.filter(
                    organization=org,
                    user=user,
                    role=OrganizationMember.Role.ADMIN
                ).exists()

                # Owner is effectively an admin
                if not is_admin and org.owner != user:
                    raise serializers.ValidationError(
                        {"organization": "You must be an Admin to create polls for this organization."})
            except Organization.DoesNotExist:
                raise serializers.ValidationError({"organization": "Organization not found."})

        # --- Freemium Limit (5 Polls/Month) ---
        # Only apply limit if it's a personal poll (not org) and user is not premium
        # Assuming you have an is_premium field or method on User
        is_premium = getattr(user, 'is_premium', False)

        if not org_id and not is_premium:
            now = timezone.now()
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            polls_this_month = Poll.objects.filter(
                creator=user,
                organization__isnull=True,
                created_at__gte=month_start
            ).count()

            if polls_this_month >= 5:
                raise serializers.ValidationError(
                    "You have reached your limit of 5 polls per month. Upgrade to Premium for unlimited polls."
                )

        # --- Option Validation ---
        if len(attrs.get('options')) < 2:
            raise serializers.ValidationError({"options": "A poll must have at least 2 options."})

        return attrs

    def create(self, validated_data):
        options_data = validated_data.pop('options')
        org_id = validated_data.pop('organization_id', None)
        user = self.context['request'].user

        with transaction.atomic():
            # Create Poll
            poll = Poll.objects.create(
                creator=user,
                organization_id=org_id,
                **validated_data
            )

            # Create Options
            poll_options = [
                PollOption(poll=poll, **option_data)
                for option_data in options_data
            ]
            PollOption.objects.bulk_create(poll_options)

        return poll


class PollListSerializer(serializers.ModelSerializer):
    """Lighter serializer for listing polls"""
    category = serializers.CharField(source='category.name')
    creator = serializers.CharField(source='creator.first_name')
    options_count = serializers.IntegerField(source='options.count', read_only=True)

    class Meta:
        model = Poll
        fields = [
            'id', 'question', 'category', 'creator',
            'start_date', 'end_date', 'is_active',
            'is_public', 'options_count', 'organization'
        ]


class VoteSerializer(serializers.ModelSerializer):
    option_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Vote
        fields = ['id', 'option_id', 'poll', 'created_at']
        read_only_fields = ['id', 'poll', 'created_at']

    def validate(self, attrs):
        request = self.context['request']
        user = request.user if request.user.is_authenticated else None
        ip_address = get_client_ip(request)

        # We get the Poll ID from the URL in the View, passed via context or saving logic
        # But here we rely on the view passing the poll object or we look up via option
        option_id = attrs.get('option_id')
        option = get_object_or_404(PollOption, pk=option_id)
        poll = option.poll

        # --- Is Poll Active? ---
        if not poll.is_active or poll.is_expired:
            raise serializers.ValidationError("This poll is closed.")

        # --- Organization Restrictions ---
        if not poll.is_public:
            # Private poll: User MUST be logged in + Member of Org
            if not user:
                raise serializers.ValidationError("You must be logged in to vote in this poll.")

            is_member = OrganizationMember.objects.filter(
                organization=poll.organization,
                user=user
            ).exists()

            if not is_member:
                raise serializers.ValidationError("You are not a member of the organization hosting this poll.")

        # --- Geo-Restrictions ---
        if poll.allowed_country:
            user_country = get_country_from_ip(ip_address)
            # If we can't determine IP (None), we strictly block if country is required
            if user_country != poll.allowed_country:
                raise serializers.ValidationError(f"This poll is restricted to voters in {poll.allowed_country}.")

        # --- Duplicate Voting Check ---
        # Authenticated User Check
        if user:
            if Vote.objects.filter(poll=poll, user=user).exists():
                raise serializers.ValidationError("You have already voted in this poll.")

        # B. IP Address Check (for both Anon and Auth users to prevent rigging)
        # Note: In some org environments, everyone shares 1 IP.
        # If it's an ORG poll, we might skip IP check and rely on User ID.
        should_check_ip = poll.is_public or (not poll.is_public and not user)

        if should_check_ip:
            if Vote.objects.filter(poll=poll, ip_address=ip_address).exists():
                raise serializers.ValidationError("A vote has already been cast from this IP address.")

        # Store context for the save method
        attrs['poll'] = poll
        attrs['option'] = option
        attrs['ip_address'] = ip_address
        return attrs

    def create(self, validated_data):
        request = self.context['request']
        user = request.user if request.user.is_authenticated else None

        # Create the vote
        vote = Vote.objects.create(
            poll=validated_data['poll'],
            option=validated_data['option'],
            ip_address=validated_data['ip_address'],
            user=user
        )
        return vote