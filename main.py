import asyncio
import json
import random
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)
class CarBookingDatabase:
    def __init__(self):
        self.bookings = {}
        self.booking_counter = 1000
        
        # Mock car data
        self.cars_by_city = {
            "Mumbai": [
                {"carType": "Sedan", "carRentalCompanyName": "Zoom Cars", "pricePerDay": 2500},
                {"carType": "SUV", "carRentalCompanyName": "Zoom Cars", "pricePerDay": 4500},
                {"carType": "Hatchback", "carRentalCompanyName": "Zoomcar", "pricePerDay": 1800},
                {"carType": "Luxury", "carRentalCompanyName": "Hertz", "pricePerDay": 8000},
            ],
            "Delhi": [
                {"carType": "Sedan", "carRentalCompanyName": "Ola Rentals", "pricePerDay": 2200},
                {"carType": "SUV", "carRentalCompanyName": "Ola Rentals", "pricePerDay": 4200},
                {"carType": "Hatchback", "carRentalCompanyName": "Revv", "pricePerDay": 1600},
                {"carType": "Luxury", "carRentalCompanyName": "Avis", "pricePerDay": 7500},
            ],
            "Bangalore": [
                {"carType": "Sedan", "carRentalCompanyName": "Zoom Cars", "pricePerDay": 2300},
                {"carType": "SUV", "carRentalCompanyName": "Zoom Cars", "pricePerDay": 4300},
                {"carType": "Hatchback", "carRentalCompanyName": "Revv", "pricePerDay": 1700},
                {"carType": "Luxury", "carRentalCompanyName": "Hertz", "pricePerDay": 7800},
            ],
            "Hyderabad": [
                {"carType": "Sedan", "carRentalCompanyName": "Zoom Cars", "pricePerDay": 2100},
                {"carType": "SUV", "carRentalCompanyName": "Zoom Cars", "pricePerDay": 4000},
                {"carType": "Hatchback", "carRentalCompanyName": "Zoomcar", "pricePerDay": 1500},
                {"carType": "Luxury", "carRentalCompanyName": "Avis", "pricePerDay": 7200},
            ]
        }

    def calculate_days(self, from_date: str, to_date: str) -> int:
        """Calculate number of days between dates"""
        start = datetime.strptime(from_date, "%Y-%m-%d")
        end = datetime.strptime(to_date, "%Y-%m-%d")
        return (end - start).days + 1
    
    def list_cars(self, city: str, from_date: str, to_date: str) -> Dict[str, Any]:
        """List available cars for a city and date range"""
        try:
            if city not in self.cars_by_city:
                return {
                    "success": False,
                    "error": f"No cars available in {city}",
                    "availableCars": []
                }
            
            days = self.calculate_days(from_date, to_date)
            cars = []
            
            for car in self.cars_by_city[city]:
                car_info = car.copy()
                car_info["days"] = days
                car_info["totalPrice"] = car["pricePerDay"] * days
                cars.append(car_info)
            
            return {
                "success": True,
                "city": city,
                "fromDate": from_date,
                "toDate": to_date,
                "duration": f"{days} days",
                "availableCars": cars
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "availableCars": []
            }

    def book_car(self, city: str, from_date: str, to_date: str, car_type: str) -> Dict[str, Any]:
        """Book a car"""
        try:
            if city not in self.cars_by_city:
                return {
                    "success": False,
                    "error": f"No cars available in {city}"
                }
            
            # Find the car
            car = None
            for c in self.cars_by_city[city]:
                if c["carType"] == car_type:
                    car = c
                    break
            
            if not car:
                return {
                    "success": False,
                    "error": f"Car type {car_type} not available in {city}"
                }
            
            days = self.calculate_days(from_date, to_date)
            total_price = car["pricePerDay"] * days
            
            booking_number = self.booking_counter
            self.booking_counter += 1
            
            # Store booking
            self.bookings[booking_number] = {
                "bookingNumber": booking_number,
                "city": city,
                "fromDate": from_date,
                "toDate": to_date,
                "carType": car_type,
                "company": car["carRentalCompanyName"],
                "pricePerDay": car["pricePerDay"],
                "totalDays": days,
                "totalPrice": total_price,
                "status": "Confirmed",
                "paymentStatus": "Pending",
                "createdAt": datetime.now().isoformat()
            }
            return {
                "success": True,
                "message": "Car booked successfully",
                "bookingNumber": booking_number,
                "totalPrice": total_price,
                "status": "Confirmed",
                "paymentStatus": "Pending"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def make_payment(self, booking_number: int, price: int) -> Dict[str, Any]:
        """Process payment for a booking"""
        try:
            if booking_number not in self.bookings:
                return {
                    "success": False,
                    "error": f"Booking #{booking_number} not found"
                }
            
            booking = self.bookings[booking_number]
            
            if booking["totalPrice"] != price:
                return {
                    "success": False,
                    "error": f"Payment amount mismatch. Expected: ₹{booking['totalPrice']}, Received: ₹{price}"
                }
            
            if booking["paymentStatus"] == "Paid":
                return {
                    "success": False,
                    "error": "Payment already completed for this booking"
                }
            # Process payment
            transaction_id = f"TXN{random.randint(100000, 999999)}"
            booking["paymentStatus"] = "Paid"
            booking["transactionId"] = transaction_id
            booking["paidAt"] = datetime.now().isoformat()
            
            return {
                "success": True,
                "message": "Payment processed successfully",
                "transactionId": transaction_id,
                "bookingNumber": booking_number,
                "amount": price,
                "status": "Paid"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    def get_booking_status(self, booking_number: int) -> Dict[str, Any]:
        """Get booking status"""
        try:
            if booking_number not in self.bookings:
                return {
                    "success": False,
                    "error": f"Booking #{booking_number} not found"
                }
            
            booking = self.bookings[booking_number]
            
            return {
                "success": True,
                "booking": booking
            }  
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
# Create the database instance
db = CarBookingDatabase()
# Create the MCP server
server = Server("car-booking-server")
@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    return [
        Tool(
            name="listCars",
            description="List available cars for rental in a city for specified dates",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City where you want to rent a car"
                    },
                    "fromDate": {
                        "type": "string",
                        "description": "Start date for rental (YYYY-MM-DD format)"
                    },
                    "toDate": {
                        "type": "string", 
                        "description": "End date for rental (YYYY-MM-DD format)"
                    }
                },
                "required": ["city", "fromDate", "toDate"]
            }
        ),
        Tool(
            name="bookCar",
            description="Book a car for the specified period",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City where you want to rent the car"
                    },
                    "fromDate": {
                        "type": "string",
                        "description": "Start date for rental (YYYY-MM-DD format)"
                    },
                    "toDate": {
                        "type": "string",
                        "description": "End date for rental (YYYY-MM-DD format)"
                    },
                    "carType": {
                        "type": "string",
                        "description": "Type of car to book (Sedan, SUV, Hatchback, Luxury)"
                    }
                },
                "required": ["city", "fromDate", "toDate", "carType"]
            }
        ),
        Tool(
            name="makePayment",
            description="Process payment for a car booking",
            inputSchema={
                "type": "object",
                "properties": {
                    "bookingNumber": {
                        "type": "integer",
                        "description": "Booking number to make payment for"
                    },
                    "price": {
                        "type": "integer",
                        "description": "Amount to pay"
                    }
                },
                "required": ["bookingNumber", "price"]
            }
        ),
        Tool(
            name="getBookingStatus",
            description="Get status of a booking",
            inputSchema={
                "type": "object",
                "properties": {
                    "bookingNumber": {
                        "type": "integer",
                        "description": "Booking number to check status for"
                    }
                },
                "required": ["bookingNumber"]
            }
        )
    ]
@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> List[TextContent]:
    """Handle tool calls."""
    
    if name == "listCars":
        city = arguments.get("city")
        from_date = arguments.get("fromDate")
        to_date = arguments.get("toDate")
        
        result = db.list_cars(city, from_date, to_date)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    elif name == "bookCar":
        city = arguments.get("city")
        from_date = arguments.get("fromDate")
        to_date = arguments.get("toDate")
        car_type = arguments.get("carType")
        
        result = db.book_car(city, from_date, to_date, car_type)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    elif name == "makePayment":
        booking_number = arguments.get("bookingNumber")
        price = arguments.get("price")
        
        result = db.make_payment(booking_number, price)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    elif name == "getBookingStatus":
        booking_number = arguments.get("bookingNumber")
        
        result = db.get_booking_status(booking_number)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    else:
        raise ValueError(f"Unknown tool: {name}")

async def main():
    # Run the server using stdin/stdout streams
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())