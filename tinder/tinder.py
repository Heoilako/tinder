import json
import logging
from datetime import datetime
from typing import Tuple, List
import random
import requests
from tinder.entities.update import Update
from tinder.entities.match import Match
from tinder.exceptions import Unauthorized, LoginException
from tinder.http import Http
from tinder.entities.user import UserProfile, LikePreview, Recommendation, SelfUser, LikedUser
import time

class TinderClient:
    """
    The client can send requests to the Tinder API.
    """

    def __init__(self, auth_token: str, proxy_dict={}, log_level: int = logging.INFO, ratelimit: int = 10):
        """
        Constructs a new client.

        :param auth_token: the X-Auth-Token
        :param proxy_dict: dictionary of proxy settings
        :param log_level: the log level, default INFO
        :param ratelimit: the ratelimit multiplier, default 10
        """

        # Logger setup
        self.logger = logging.getLogger(f"TinderClient_{auth_token}")  
        self.logger.setLevel(log_level)
        handler = logging.StreamHandler()  # You can change this to FileHandler to log to files
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        if not self.logger.handlers:
            self.logger.addHandler(handler)

        self.logger.info("Initializing TinderClient")

        self._http = Http(auth_token, proxy_dict, log_level, ratelimit)
        self._self_user = None
        self._matches: dict = {}

        try:
            self._self_user = self.get_self_user()
        except Unauthorized as e:
            self.logger.error("Unauthorized access, login failed.")
            raise LoginException("Unauthorized access, login failed.")
        if self._self_user is None:
            self.logger.error("Failed to retrieve self user, login failed.")
            raise LoginException("Failed to retrieve self user, login failed.")
        self.active = True
        self.logger.info("TinderClient initialized successfully")

    def invalidate_match(self, match: Match):
        """
        Removes a match from the cache.

        :param match: the match to invalidate
        """
        self.logger.info(f"Invalidating match with ID: {match.id}")
        self._matches.pop(match.id, None)

    def invalidate_self_user(self):
        """
        Invalidates the cached self user.
        """
        self.logger.info("Invalidating cached self user")
        self._self_user = None

    def get_updates(self, last_activity_date: str = "") -> Update:
        """
        Gets updates from the Tinder API, such as new matches or new messages.

        :param last_activity_date: The last activity date to get updates from.
        :return: updates from the Tinder API
        """
        self.logger.info("Fetching updates")
        if last_activity_date == "":
            last_activity_date = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.00Z")
        response = self._http.make_request(
            method="POST",
            route="/updates",
            body={"nudge": True, "last_activity_date": f"{last_activity_date}"},
        ).json()
        self.logger.info("Updates fetched successfully")
        return Update(response)

    def get_recommendations(self) -> Tuple[Recommendation]:
        """
        Gets recommended users.

        :return: a tuple of recommended users
        """
        self.logger.info("Fetching recommendations")
        response = self._http.make_request(method="GET", route="/recs/core").json()
        self.logger.info("Recommendations fetched successfully")
        return tuple(Recommendation(r, self._http) for r in response["results"])

    def get_like_previews(self) -> Tuple[LikePreview]:
        """
        Gets users that liked the self user.

        :return: a tuple of users that liked the self user
        """
        self.logger.info("Fetching like previews")
        response = self._http.make_request(method="GET", route="/v2/fast-match/teasers").json()
        self.logger.info("Like previews fetched successfully")
        return tuple(LikePreview(user["user"], self._http) for user in response["data"]["results"])

    def load_all_matches(self, page_token: str = None) -> Tuple[Match]:
        """
        Gets all matches from the Tinder API.

        :param page_token: The pagination token for loading more matches.
        :return: a tuple of all matches
        """
        self.logger.info("Loading all matches")
        route = f"/v2/matches?count=60"
        if page_token:
            route += f"&page_token={page_token}"

        data = self._http.make_request(method="GET", route=route).json()["data"]
        matches = [Match(m, self._http, self) for m in data["matches"]]
        if "next_page_token" in data:
            matches.extend(self.load_all_matches(data["next_page_token"]))

        self._matches = {match.id: match for match in matches}
        self.logger.info("All matches loaded successfully")
        return tuple(matches)

    def get_match(self, match_id: str) -> Match:
        """
        Gets a match by id.

        :param match_id: the match id
        :return: a match by id
        """
        self.logger.info(f"Fetching match with ID: {match_id}")
        if match_id in self._matches:
            return self._matches[match_id]
        else:
            response = self._http.make_request(method="GET", route=f"/v2/matches/{match_id}").json()
            match = Match(response["data"], self._http, self)
            self._matches[match.id] = match
            self.logger.info(f"Match with ID: {match_id} fetched successfully")
            return match

    def get_user_profile(self, user_id: str) -> UserProfile:
        """
        Gets a user profile by id.

        :param user_id: the user id
        :return: a user profile by id
        """
        self.logger.info(f"Fetching user profile with ID: {user_id}")
        response = self._http.make_request(method="GET", route=f"/user/{user_id}").json()
        self.logger.info(f"User profile with ID: {user_id} fetched successfully")
        return UserProfile(response["results"], self._http)

    def get_self_user(self) -> SelfUser:
        """
        Gets the self user.

        :return: the self user
        """
        if self._self_user is None:
            self.logger.info("Fetching self user profile.")
            response = self._http.make_request(method="GET", route="/profile").json()
            self._self_user = SelfUser(response, self._http)
            self.logger.info("Self user profile fetched successfully.")
        return self._self_user

    def get_liked_users(self) -> Tuple[LikedUser]:
        """
        Gets all users that the self user liked.

        :return: a tuple of all liked users
        """
        self.logger.info("Fetching liked users")
        response = self._http.make_request(method="GET", route="/v2/my-likes").json()
        result = []
        for user in response["data"]["results"]:
            transformed = {}
            transformed.update(user.items())
            transformed.pop("type")
            transformed.pop("user")
            transformed.update(user["user"].items())
            result.append(transformed)
        self.logger.info("Liked users fetched successfully")
        return tuple(LikedUser(user, self._http) for user in result)

    def update_bio(self, new_bio: str) -> bool:
        """
        Updates the bio of the user's profile.

        :param new_bio: The new bio to set for the profile.
        :return: True if the update was successful, False otherwise.
        """
        self.logger.info(f"Updating bio to: {new_bio}")
        payload = {"bio": new_bio}
        response = self._http.make_request(method="POST", route="/profile", body=payload)

        if response.status_code == 200:
            self.logger.info("Bio updated successfully")
            return True
        else:
            self.logger.error(f"Failed to update bio. Status code: {response.status_code}")
            return False

    def swipe_routine(self, start_hour: int, end_hour: int, likes_per_day: int):
        """
        Executes a routine of swiping likes based on the specified time range and likes per day.

        :param start_hour: The hour to start the routine.
        :param end_hour: The hour to end the routine.
        :param likes_per_day: The maximum number of likes to perform in the routine.
        """
        self.logger.info(f"Starting swipe routine from {start_hour} to {end_hour} with {likes_per_day} likes per day")
        now = datetime.now()
        start_time = datetime(now.year, now.month, now.day, start_hour)
        end_time = datetime(now.year, now.month, now.day, end_hour)

        if start_time <= now <= end_time:
            likes_count = 0
            while likes_count < likes_per_day:
                recommendations = self.get_recommendations()
                for recommendation in recommendations:
                    recommendation.like()
                    likes_count += 1
                    if likes_count >= likes_per_day:
                        break
                    time.sleep(random.randint(1, 5))  # Wait for 1-5 seconds between likes to mimic human behavior
            self.logger.info(f"Completed swipe routine with {likes_count} likes")
        else:
            self.logger.info("Not within the swipe routine time.")

    def get_api_token(self, refresh_token):
        """
        Retrieves a new API token using the provided refresh token.

        :param refresh_token: The refresh token used to obtain a new API token.
        :return: The new API token.
        """
        self.logger.info("Retrieving new API token")
        TOKEN_URL = "https://api.gotinder.com/v2/auth/login/sms"
        data = {'refresh_token': refresh_token}
        r = self._http.make_request(route='/v2/auth/login/sms', method='POST', body=data, verify=False)
        response = r.json()
        api_token = response.get("data", {}).get("api_token")
        if api_token:
            self.logger.info("New API token retrieved successfully")
            return api_token
        else:
            self.logger.error("Failed to retrieve new API token")
            return None
