from datetime import datetime, timezone, timedelta
from typing import Dict, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from ..crud.event import get_event_by_id
from uuid import UUID


class DynamicPricingService:
    """
    Service for calculating dynamic pricing based on time until event.
    
    Pricing tiers:
    - 4+ weeks (28+ days): Base price (1.0x)
    - 3-4 weeks (21-27 days): 25% increase (1.25x)
    - 2-3 weeks (14-20 days): 50% increase (1.5x)
    - 1-2 weeks (7-13 days): 75% increase (1.75x)
    - 0-1 week (0-6 days): 100% increase (2.0x)
    """
    
    PRICING_TIERS = [
        (28, 1.0),   # 4+ weeks: base price
        (21, 1.25),  # 3-4 weeks: +25%
        (14, 1.5),   # 2-3 weeks: +50%
        (7, 1.75),   # 1-2 weeks: +75%
        (0, 2.0),    # 0-1 week: +100%
    ]
    
    @classmethod
    def calculate_pricing_multiplier(cls, days_until_event: int) -> float:
        """
        Calculate the pricing multiplier based on days until event.
        
        Args:
            days_until_event: Number of days from now until the event
            
        Returns:
            float: Multiplier to apply to base price
        """
        for min_days, multiplier in cls.PRICING_TIERS:
            if days_until_event >= min_days:
                return multiplier
        
        # If somehow we get negative days, use the highest price tier
        return cls.PRICING_TIERS[-1][1]
    
    @classmethod
    def calculate_current_price(cls, base_price: float, event_start_time: datetime) -> float:
        """
        Calculate the current price for an event based on its start time.
        
        Args:
            base_price: The base price of the event
            event_start_time: When the event starts
            
        Returns:
            float: Current price for the event
        """
        now = datetime.now(timezone.utc)
        days_until_event = (event_start_time - now).days
        
        # If event has already started or passed, return base price
        if days_until_event < 0:
            return base_price
        
        multiplier = cls.calculate_pricing_multiplier(days_until_event)
        return round(base_price * multiplier, 2)
    
    @classmethod
    async def get_event_current_price(cls, db: AsyncSession, event_id: UUID) -> float:
        """
        Get the current price for a specific event.
        
        Args:
            db: Database session
            event_id: ID of the event
            
        Returns:
            float: Current price for the event
            
        Raises:
            ValueError: If event not found
        """
        event = await get_event_by_id(db, event_id)
        if not event:
            raise ValueError("Event not found")
        
        return cls.calculate_current_price(event.base_price, event.start_time)
    
    @classmethod
    def get_pricing_timeline(cls, base_price: float, event_start_time: datetime) -> List[Dict]:
        """
        Get the complete pricing timeline for an event.
        
        Args:
            base_price: The base price of the event
            event_start_time: When the event starts
            
        Returns:
            List[Dict]: Timeline with dates and prices
        """
        now = datetime.now(timezone.utc)
        timeline = []
        
        for min_days, multiplier in cls.PRICING_TIERS:
            tier_start = event_start_time - timedelta(days=min_days)
            
            # Only include future or current tiers
            if tier_start <= now:
                tier_start = now
            
            price = round(base_price * multiplier, 2)
            
            timeline.append({
                "start_date": tier_start.isoformat(),
                "days_before_event": min_days,
                "price_multiplier": multiplier,
                "price": price,
                "percentage_increase": round((multiplier - 1) * 100, 0)
            })
        
        return sorted(timeline, key=lambda x: x["days_before_event"], reverse=True)
    
    @classmethod
    async def get_event_pricing_timeline(cls, db: AsyncSession, event_id: UUID) -> Dict:
        """
        Get the complete pricing timeline for a specific event.
        
        Args:
            db: Database session
            event_id: ID of the event
            
        Returns:
            Dict: Event pricing information with timeline
            
        Raises:
            ValueError: If event not found
        """
        event = await get_event_by_id(db, event_id)
        if not event:
            raise ValueError("Event not found")
        
        current_price = cls.calculate_current_price(event.base_price, event.start_time)
        timeline = cls.get_pricing_timeline(event.base_price, event.start_time)
        
        now = datetime.now(timezone.utc)
        days_until_event = (event.start_time - now).days
        
        return {
            "event_id": event_id,
            "event_name": event.name,
            "event_start_time": event.start_time.isoformat(),
            "base_price": event.base_price,
            "current_price": current_price,
            "days_until_event": max(0, days_until_event),
            "current_multiplier": cls.calculate_pricing_multiplier(max(0, days_until_event)),
            "pricing_timeline": timeline
        }
    
    @classmethod
    def calculate_total_booking_cost(cls, base_price: float, event_start_time: datetime, num_tickets: int) -> Dict:
        """
        Calculate the total cost for a booking with multiple tickets.
        
        Args:
            base_price: The base price per ticket
            event_start_time: When the event starts
            num_tickets: Number of tickets being booked
            
        Returns:
            Dict: Breakdown of booking costs
        """
        current_price = cls.calculate_current_price(base_price, event_start_time)
        total_cost = current_price * num_tickets
        
        now = datetime.now(timezone.utc)
        days_until_event = (event_start_time - now).days
        
        return {
            "base_price_per_ticket": base_price,
            "current_price_per_ticket": current_price,
            "number_of_tickets": num_tickets,
            "total_cost": round(total_cost, 2),
            "days_until_event": max(0, days_until_event),
            "price_multiplier": cls.calculate_pricing_multiplier(max(0, days_until_event)),
            "savings_if_base_price": round((base_price * num_tickets) - total_cost, 2) if current_price > base_price else 0
        }
