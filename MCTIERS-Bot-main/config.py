GUILD_ID = 1
LOGGING_CHANNEL_ID = 1
FOOTER_ICON_URL = ""

# --- Categories ---
EU_TESTING_CATEGORY_ID = 1
NA_TESTING_CATEGORY_ID = 1
AS_AU_TESTING_CATEGORY_ID = 1
HIGH_TESTING_CATEGORY_ID = 1
TESTING_OVERFLOW_CATEGORY_ID = 1

# --- Channels ---
REQUEST_TEST_CHANNEL_ID = 1
RESULTS_CHANNEL_ID = 1
LEADERBOARD_CHANNEL_ID = 1
TRANSCRIPTS_CHANNEL_ID = 1
TESTS_END_OF_THE_MONTH_CHANNEL_ID = 1
FAILED_QUOTA_TESTERS_CHANNEL_ID = 1
NA_WAITLIST_CHANNEL_ID = 1
AS_AU_WAITLIST_CHANNEL_ID = 1
EU_WAITLIST_CHANNEL_ID = 1
QUEUE_JOIN_CHANNEL_ID = 1

TESTER_QUOTA = 0

# --- Roles ---
OWNER_ROLE_ID = 1
MANAGER_ROLE_ID = 1
DEVELOPER_ROLE_ID = 1
TIERLIST_ADMIN_ROLE_ID = 1
REGULATOR_ROLE_ID = 1
MODERATOR_ROLE_ID = 1
SENIOR_TESTER_ROLE_ID = 1 
TESTER_ROLE_ID = 1
BOOSTER_ROLE_ID = 1
QUOTA_EXEMPT_ROLE_ID = 1

EU_REGION_ROLE_ID = 1
NA_REGION_ROLE_ID = 1
AS_AU_REGION_ROLE_ID = 1

EU_WAITLIST_ROLE_ID = 1
NA_WAITLIST_ROLE_ID = 1
AS_AU_WAITLIST_ROLE_ID = 1

HT1_ROLE_ID = 1
LT1_ROLE_ID = 1
HT2_ROLE_ID = 1
LT2_ROLE_ID = 1
HT3_ROLE_ID = 1
LT3_ROLE_ID = 1
HT4_ROLE_ID = 1
LT4_ROLE_ID = 1
HT5_ROLE_ID = 1
LT5_ROLE_ID = 1

MAX_QUEUE_SIZE = 20

REGION_DATA = {
    "na": {"waitlist_role_id": NA_WAITLIST_ROLE_ID, "channel_id": NA_WAITLIST_CHANNEL_ID, "category_id": NA_TESTING_CATEGORY_ID, "region_role_id": NA_REGION_ROLE_ID},
    "eu": {"waitlist_role_id": EU_WAITLIST_ROLE_ID, "channel_id": EU_WAITLIST_CHANNEL_ID, "category_id": EU_TESTING_CATEGORY_ID, "region_role_id": EU_REGION_ROLE_ID},
    "as": {"waitlist_role_id": AS_AU_WAITLIST_ROLE_ID, "channel_id": AS_AU_WAITLIST_CHANNEL_ID, "category_id": AS_AU_TESTING_CATEGORY_ID, "region_role_id": AS_AU_REGION_ROLE_ID},
    "au": {"maps_to": "as"}, 
    "me": {"maps_to": "eu"},
    "af": {"maps_to": "eu"},
    "sa": {"maps_to": "na"},
}

tier_points = {"HT1": 60, "LT1": 45, "HT2": 30, "LT2": 20, "HT3": 10, "LT3": 6, "HT4": 4, "LT4": 3, "HT5": 2, "LT5": 1}

rank_roles_dict = {
    "HT1": HT1_ROLE_ID, "LT1": LT1_ROLE_ID, "HT2": HT2_ROLE_ID, "LT2": LT2_ROLE_ID,
    "HT3": HT3_ROLE_ID, "LT3": LT3_ROLE_ID, "HT4": HT4_ROLE_ID, "LT4": LT4_ROLE_ID,
    "HT5": HT5_ROLE_ID, "LT5": LT5_ROLE_ID,
}

rank_full_names = {
    "HT1": "High Tier 1", "LT1": "Low Tier 1", "HT2": "High Tier 2", "LT2": "Low Tier 2",
    "HT3": "High Tier 3", "LT3": "Low Tier 3", "HT4": "High Tier 4", "LT4": "Low Tier 4",
    "HT5": "High Tier 5", "LT5": "Low Tier 5", "Unranked": "Unranked"
}

tier_ranking = ["HT1", "LT1", "HT2", "LT2", "HT3", "LT3", "HT4", "LT4", "HT5", "LT5", "Unranked"]
high_testing_tiers = {"HT1", "LT1", "HT2", "LT2", "HT3"}