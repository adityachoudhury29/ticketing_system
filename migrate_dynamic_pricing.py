#!/usr/bin/env python3
"""
Migration script to add dynamic pricing columns to the bookings table.

This script adds the following columns to the bookings table:
- base_price_per_ticket: Float (NOT NULL)
- final_price_per_ticket: Float (NOT NULL) 
- price_multiplier: Float (NOT NULL, default 1.0)
- total_amount: Float (NOT NULL)

For existing bookings, the script will:
1. Use the event's base_price for both base_price_per_ticket and final_price_per_ticket
2. Set price_multiplier to 1.0
3. Calculate total_amount as final_price_per_ticket * number_of_tickets

Run this script BEFORE starting the application with the new pricing features.
"""

import asyncio
import sys
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, ProgrammingError
from app.db.session import engine


async def check_column_exists(conn, table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table"""
    try:
        result = await conn.execute(text(f"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = '{table_name}' AND column_name = '{column_name}'
        """))
        return result.first() is not None
    except Exception:
        return False


async def add_dynamic_pricing_columns():
    """Add dynamic pricing columns to the bookings table"""
    
    async with engine.begin() as conn:
        print("Starting dynamic pricing migration...")
        
        # Check if columns already exist
        columns_to_add = [
            'base_price_per_ticket',
            'final_price_per_ticket', 
            'price_multiplier',
            'total_amount'
        ]
        
        existing_columns = []
        for column in columns_to_add:
            if await check_column_exists(conn, 'bookings', column):
                existing_columns.append(column)
        
        if existing_columns:
            print(f"Columns already exist: {existing_columns}")
            print("Skipping column creation...")
        else:
            print("Adding new columns to bookings table...")
            
            # Add the new columns (allowing NULL initially)
            await conn.execute(text("""
                ALTER TABLE bookings 
                ADD COLUMN base_price_per_ticket FLOAT,
                ADD COLUMN final_price_per_ticket FLOAT,
                ADD COLUMN price_multiplier FLOAT DEFAULT 1.0,
                ADD COLUMN total_amount FLOAT;
            """))
            print("✓ Added new columns")
        
        # Update existing bookings with calculated values
        print("Updating existing bookings with pricing data...")
        
        # Get count of bookings that need updating
        result = await conn.execute(text("""
            SELECT COUNT(*) as count 
            FROM bookings 
            WHERE base_price_per_ticket IS NULL;
        """))
        bookings_to_update = result.scalar()
        
        if bookings_to_update > 0:
            print(f"Found {bookings_to_update} bookings to update...")
            
            # Update existing bookings with event base prices
            await conn.execute(text("""
                UPDATE bookings 
                SET 
                    base_price_per_ticket = events.base_price,
                    final_price_per_ticket = events.base_price,
                    price_multiplier = 1.0,
                    total_amount = events.base_price * (
                        SELECT COUNT(*) 
                        FROM tickets 
                        WHERE tickets.booking_id = bookings.id
                    )
                FROM events 
                WHERE bookings.event_id = events.id 
                AND bookings.base_price_per_ticket IS NULL;
            """))
            print("✓ Updated existing bookings with pricing data")
        else:
            print("✓ No existing bookings need updating")
        
        # Make columns NOT NULL after populating data
        if not existing_columns:
            print("Setting columns to NOT NULL...")
            await conn.execute(text("""
                ALTER TABLE bookings 
                ALTER COLUMN base_price_per_ticket SET NOT NULL,
                ALTER COLUMN final_price_per_ticket SET NOT NULL,
                ALTER COLUMN price_multiplier SET NOT NULL,
                ALTER COLUMN total_amount SET NOT NULL;
            """))
            print("✓ Set columns to NOT NULL")
    
    print("✅ Dynamic pricing migration completed successfully!")


async def verify_migration():
    """Verify the migration was successful"""
    async with engine.begin() as conn:
        print("\nVerifying migration...")
        
        # Check column structure
        result = await conn.execute(text("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'bookings' 
            AND column_name IN ('base_price_per_ticket', 'final_price_per_ticket', 'price_multiplier', 'total_amount')
            ORDER BY column_name;
        """))
        
        columns = result.fetchall()
        print("New columns in bookings table:")
        for col in columns:
            print(f"  - {col.column_name}: {col.data_type} (nullable: {col.is_nullable})")
        
        # Check data
        result = await conn.execute(text("""
            SELECT COUNT(*) as total_bookings,
                   COUNT(base_price_per_ticket) as with_pricing
            FROM bookings;
        """))
        
        stats = result.first()
        print(f"\nBookings data:")
        print(f"  - Total bookings: {stats.total_bookings}")
        print(f"  - Bookings with pricing data: {stats.with_pricing}")
        
        if stats.total_bookings == stats.with_pricing:
            print("✅ All bookings have pricing data!")
        else:
            print("❌ Some bookings are missing pricing data!")
            return False
    
    return True


async def main():
    """Main migration function"""
    try:
        await add_dynamic_pricing_columns()
        success = await verify_migration()
        
        if success:
            print("\n🎉 Migration completed successfully!")
            print("You can now start the application with dynamic pricing features.")
        else:
            print("\n❌ Migration verification failed!")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        print("Please check your database connection and try again.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
