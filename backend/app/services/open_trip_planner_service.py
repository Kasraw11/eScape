class OpenTripPlannerService:
    async def get_route_alternatives(
        self,
        request: RoutePlanningRequest,
    ) -> list[RouteCandidate]:

        # Send origin/destination to OpenTripPlanner.

        # OTP decides journey legs:
        # walking
        # tram
        # train
        # bus

        # Convert OTP response into RouteCandidate objects.

        ...