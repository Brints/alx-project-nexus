from dateutil.relativedelta import relativedelta
from django.utils import timezone
from django.db import transaction
from rest_framework import serializers
from .models import Poll, PollCategory, PollOption, Vote
from .utils import get_client_ip, get_country_from_ip
from organizations.models import Organization


class PollCategorySerializer(serializers.ModelSerializer):
    created_by = serializers.CharField(
        source="created_by.first_name", read_only=True, allow_null=True
    )

    class Meta:
        model = PollCategory
        fields = ["category_id", "name", "created_by", "created_at"]
        read_only_fields = ["category_id", "created_by", "created_at"]


class PollOptionSerializer(serializers.ModelSerializer):
    # CHANGE 1: Return the 'index' (1, 2, 3) as the 'id' field in JSON
    id = serializers.IntegerField(source="index", read_only=True)

    class Meta:
        model = PollOption
        fields = ["id", "text", "image", "vote_count"]
        read_only_fields = ["vote_count", "id"]


class VoteSerializer(serializers.ModelSerializer):
    poll_id = serializers.UUIDField(write_only=True)
    # CHANGE 2: This input expects the relative index (e.g., 1), not the DB PK
    option_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Vote
        fields = ["id", "poll_id", "option_id", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate(self, attrs):
        request = self.context.get("request")
        user = request.user if request and request.user.is_authenticated else None
        ip_address = get_client_ip(request)

        poll_id = attrs.get("poll_id")
        option_index = attrs.get("option_id")  # Renamed var for clarity

        try:
            poll = Poll.objects.get(pk=poll_id)
        except Poll.DoesNotExist:
            raise serializers.ValidationError("Poll not found.")

        try:
            # CHANGE 3: Lookup option by (poll + index) instead of PK
            option = PollOption.objects.get(poll=poll, index=option_index)
        except PollOption.DoesNotExist:
            raise serializers.ValidationError("Invalid option for this poll.")

        # --- Validations ---
        if not poll.is_active:
            raise serializers.ValidationError("This poll is closed.")

        if poll.is_expired:
            raise serializers.ValidationError("This poll has expired.")

        if not poll.is_public:
            if not user:
                raise serializers.ValidationError(
                    "You must be logged in to vote in this poll."
                )

            # Check Organization Membership
            if poll.organization:
                from organizations.models import OrganizationMember

                is_member = OrganizationMember.objects.filter(
                    organization=poll.organization, user=user
                ).exists()
                if not is_member:
                    raise serializers.ValidationError(
                        f"You must be a member of {poll.organization.org_name} to vote."
                    )

        if poll.allowed_country:
            user_country = get_country_from_ip(ip_address)
            if user_country != poll.allowed_country:
                raise serializers.ValidationError(
                    f"This poll is restricted to voters in {poll.allowed_country}."
                )

        # Check for duplicate votes
        if user:
            if Vote.objects.filter(poll=poll, user=user).exists():
                raise serializers.ValidationError(
                    "You have already voted in this poll."
                )
        else:
            if Vote.objects.filter(poll=poll, ip_address=ip_address).exists():
                raise serializers.ValidationError(
                    "A vote has already been cast from this IP address."
                )

        attrs["poll"] = poll
        attrs["option"] = option
        attrs["ip_address"] = ip_address
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        user = request.user if request.user.is_authenticated else None

        vote = Vote.objects.create(
            poll=validated_data["poll"],
            option=validated_data["option"],
            ip_address=validated_data["ip_address"],
            user=user,
        )
        return vote


class PollCreateSerializer(serializers.ModelSerializer):
    options = PollOptionSerializer(many=True)
    organization_id = serializers.UUIDField(
        required=False, allow_null=True, write_only=True
    )
    creator_name = serializers.CharField(source="creator.first_name", read_only=True)

    # New Duration Fields
    duration_value = serializers.IntegerField(
        write_only=True, min_value=1, help_text="The duration value (e.g., 5)"
    )
    duration_unit = serializers.ChoiceField(
        choices=[
            ("seconds", "Seconds"),
            ("minutes", "Minutes"),
            ("hours", "Hours"),
            ("days", "Days"),
            ("weeks", "Weeks"),
            ("months", "Months"),
            ("years", "Years"),
        ],
        write_only=True,
        help_text="The unit of time for the duration",
    )

    class Meta:
        model = Poll
        fields = [
            "poll_id",
            "poll_question",
            "poll_category",
            "duration_value",
            "duration_unit",
            "start_date",
            "end_date",
            "is_public",
            "options",
            "organization_id",
            "creator_name",
            "allowed_country",
        ]
        read_only_fields = ["poll_id", "start_date", "end_date", "creator_name"]

    def create(self, validated_data):
        # Extract non-model fields
        options_data = validated_data.pop("options")
        org_id = validated_data.pop("organization_id", None)

        # Extract Duration Data
        duration_val = validated_data.pop("duration_value")
        duration_unit = validated_data.pop("duration_unit")

        # Calculate Dates
        start_date = timezone.now()

        # Using relativedelta to handle years/months correctly
        time_delta_kwargs = {duration_unit: duration_val}
        end_date = start_date + relativedelta(**time_delta_kwargs)

        validated_data["start_date"] = start_date
        validated_data["end_date"] = end_date

        # Handle Organization Linking
        if org_id:
            try:
                org = Organization.objects.get(pk=org_id)
                validated_data["organization"] = org
            except Organization.DoesNotExist:
                raise serializers.ValidationError(
                    {"organization_id": "Invalid Organization ID."}
                )

        # Create Poll & Options Atomically
        with transaction.atomic():
            poll = Poll.objects.create(**validated_data)

            # Assign index 1, 2, 3... during creation
            for i, option_data in enumerate(options_data):
                PollOption.objects.create(poll=poll, index=i + 1, **option_data)

        return poll


class PollListSerializer(serializers.ModelSerializer):
    """
    Lighter serializer for listing polls.
    """

    creator_name = serializers.CharField(source="creator.first_name", read_only=True)
    category_name = serializers.CharField(source="poll_category.name", read_only=True)
    total_votes = serializers.SerializerMethodField()
    has_voted = serializers.SerializerMethodField()

    class Meta:
        model = Poll
        fields = [
            "poll_id",
            "poll_question",
            "category_name",
            "creator_name",
            "start_date",
            "end_date",
            "is_active",
            "is_public",
            "total_votes",
            "has_voted",
            "is_expired",
        ]

    def get_total_votes(self, obj):
        # Sum the pre-calculated vote_counts from options
        return sum(opt.vote_count for opt in obj.options.all())

    def get_has_voted(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return Vote.objects.filter(poll=obj, user=request.user).exists()
        return False
