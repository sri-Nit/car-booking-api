import asyncio
import json
import subprocess
import sys
import os
from datetime import datetime, date
from typing import Dict, Any, List, Optional
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client

class CarBookingMCPClient:
    """MCP Client for Car Booking Service"""
    
    def __init__(self, server_command: List[str]):
    
        self.server_command = server_command
        self.session = None
        self.server_process = None
        self._stdio_context = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        try:
            # Start the MCP server process with proper Windows handling
            if os.name == 'nt':  # Windows
                self.server_process = await asyncio.create_subprocess_exec(
                    *self.server_command,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                )
            else:  
                self.server_process = await asyncio.create_subprocess_exec(
                    *self.server_command,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            
            # Wait a moment for server to start
            await asyncio.sleep(2)
            
            # Check if server started successfully
            if self.server_process.returncode is not None:
                stderr_output = await self.server_process.stderr.read()
                raise Exception(f"Server failed to start: {stderr_output.decode()}")
            
            # Create stdio client with proper stream handling
            # The stdio_client function expects stdin and stdout streams
            self._stdio_context = stdio_client(
                self.server_process.stdin,  # write stream
                self.server_process.stdout  # read stream
            )
            
            # Enter the stdio client context to get the session
            self.session = await self._stdio_context.__aenter__()
            
            # Initialize the session
            init_result = await self.session.initialize()
            print(f"✅ MCP Session initialized: {init_result}")
            
            return self
            
        except Exception as e:
            # Cleanup on error
            await self._cleanup()
            raise Exception(f"Failed to initialize MCP client: {str(e)}")
    
    async def _cleanup(self):
        """Helper method to cleanup resources"""
        try:
            # Close stdio context first
            if self._stdio_context:
                await self._stdio_context.__aexit__(None, None, None)
        except Exception as e:
            print(f"Warning: Error closing stdio context: {e}")
        
        try:
            # Terminate server process
            if self.server_process:
                self.server_process.terminate()
                try:
                    await asyncio.wait_for(self.server_process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    self.server_process.kill()
                    await self.server_process.wait()
        except Exception as e:
            print(f"Warning: Error terminating server process: {e}")
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self._cleanup()
    
    async def list_available_tools(self) -> List[str]:
        """List all available tools from the MCP server"""
        try:
            if not self.session:
                raise Exception("Session not initialized")
            
            tools_result = await self.session.list_tools()
            return [tool.name for tool in tools_result.tools]
        except Exception as e:
            print(f"Error listing tools: {e}")
            return []
    
    async def list_cars(self, city: str, from_date: str, to_date: str) -> Dict[str, Any]:
        """List available cars for rental"""
        try:
            if not self.session:
                raise Exception("Session not initialized")
                
            result = await self.session.call_tool(
                name="listCars",
                arguments={
                    "city": city,
                    "fromDate": from_date,
                    "toDate": to_date
                }
            )
            
            if result.content and len(result.content) > 0:
                response_text = result.content[0].text
                return json.loads(response_text)
            else:
                return {"error": "No response content from server"}
            
        except Exception as e:
            return {"error": f"Failed to list cars: {str(e)}"}
    
    async def book_car(self, city: str, from_date: str, to_date: str, car_type: str) -> Dict[str, Any]:
        """Book a car for the specified period"""
        try:
            if not self.session:
                raise Exception("Session not initialized")
                
            result = await self.session.call_tool(
                name="bookCar",
                arguments={
                    "city": city,
                    "fromDate": from_date,
                    "toDate": to_date,
                    "carType": car_type
                }
            )
            
            if result.content and len(result.content) > 0:
                response_text = result.content[0].text
                return json.loads(response_text)
            else:
                return {"error": "No response content from server"}
            
        except Exception as e:
            return {"error": f"Failed to book car: {str(e)}"}
    
    async def make_payment(self, booking_number: int, price: int) -> Dict[str, Any]:
        """Process payment for a car booking"""
        try:
            if not self.session:
                raise Exception("Session not initialized")
                
            result = await self.session.call_tool(
                name="makePayment",
                arguments={
                    "bookingNumber": booking_number,
                    "price": price
                }
            )
            
            if result.content and len(result.content) > 0:
                response_text = result.content[0].text
                return json.loads(response_text)
            else:
                return {"error": "No response content from server"}
            
        except Exception as e:
            return {"error": f"Failed to process payment: {str(e)}"}
    
    async def get_booking_status(self, booking_number: int) -> Dict[str, Any]:
        """Get status of a booking"""
        try:
            if not self.session:
                raise Exception("Session not initialized")
                
            result = await self.session.call_tool(
                name="getBookingStatus",
                arguments={
                    "bookingNumber": booking_number
                }
            )
            
            if result.content and len(result.content) > 0:
                response_text = result.content[0].text
                return json.loads(response_text)
            else:
                return {"error": "No response content from server"}
            
        except Exception as e:
            return {"error": f"Failed to get booking status: {str(e)}"}


# Rest of your classes remain the same...
class BookingSession:
    """Tracks the current booking session state"""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset the booking session"""
        self.city: Optional[str] = None
        self.from_date: Optional[str] = None
        self.to_date: Optional[str] = None
        self.available_cars: List[Dict] = []
        self.selected_car: Optional[Dict] = None
        self.booking_number: Optional[int] = None
        self.total_price: Optional[int] = None
        self.booking_confirmed: bool = False
        self.payment_completed: bool = False

  
class CarBookingCLI:
    """Command Line Interface for Car Booking with Flow Management"""
    
    def __init__(self, client: CarBookingMCPClient):
        self.client = client
        self.session = BookingSession()
    
    def print_banner(self):
        """Print application banner"""
        print("=" * 60)
        print("🚗 CAR BOOKING MCP CLIENT - GUIDED FLOW")
        print("=" * 60)
    
    def print_main_menu(self):
        """Print main menu options"""
        print("\nMain Menu:")
        print("1. 🆕 Start New Booking")
        print("2. 📋 Check Existing Booking Status")
        print("3. 🔧 List Available MCP Tools")
        print("4. 🚪 Exit")
        print("-" * 40)
    
    def print_booking_flow_menu(self):
        """Print booking flow menu based on current state"""
        print(f"\n🎯 BOOKING FLOW - Step {self.get_current_step()}")
        print("-" * 40)
        
        if not self.session.city:
            print("📍 Step 1: Search for cars in your city")
        elif not self.session.selected_car:
            print("🚗 Step 2: Select a car from available options")
        elif not self.session.booking_confirmed:
            print("🎫 Step 3: Confirm your booking")
        elif not self.session.payment_completed:
            print("💳 Step 4: Complete payment")
        else:
            print("✅ Booking Complete!")
        
        print("\nOptions:")
        if not self.session.city:
            print("1. Search for Cars")
        elif not self.session.selected_car:
            print("1. Select a Car")
            print("2. Search Again (Different City/Dates)")
        elif not self.session.booking_confirmed:
            print("1. Confirm Booking")
            print("2. Choose Different Car")
            print("3. Search Again")
        elif not self.session.payment_completed:
            print("1. Make Payment")
            print("2. View Booking Details")
        else:
            print("1. View Final Booking Status")
            print("2. Start New Booking")
        
        print("0. Back to Main Menu")
        print("-" * 40)
    
    def get_current_step(self) -> int:
        """Get current step number"""
        if not self.session.city:
            return 1
        elif not self.session.selected_car:
            return 2
        elif not self.session.booking_confirmed:
            return 3
        elif not self.session.payment_completed:
            return 4
        else:
            return 5
    
    def get_user_input(self, prompt: str, input_type: str = "str"):
        """Get user input with type validation"""
        while True:
            try:
                value = input(prompt).strip()
                if not value:
                    print("❌ Input cannot be empty. Please try again.")
                    continue
                    
                if input_type == "int":
                    return int(value)
                elif input_type == "date":
                    datetime.strptime(value, "%Y-%m-%d")
                    return value
                else:
                    return value
                    
            except ValueError as e:
                if input_type == "int":
                    print("❌ Please enter a valid number.")
                elif input_type == "date":
                    print("❌ Please enter date in YYYY-MM-DD format.")
                else:
                    print(f"❌ Invalid input: {e}")
    
    async def step1_search_cars(self):
        """Step 1: Search for available cars"""
        print("\n🔍 STEP 1: SEARCH FOR CARS")
        print("-" * 30)
        
        city = self.get_user_input("🏙️  Enter city: ")
        from_date = self.get_user_input("📅 Enter from date (YYYY-MM-DD): ", "date")
        to_date = self.get_user_input("📅 Enter to date (YYYY-MM-DD): ", "date")
        
        print("\n⏳ Searching for available cars...")
        cars_data = await self.client.list_cars(city, from_date, to_date)
        
        if "error" in cars_data:
            print(f"❌ Error: {cars_data['error']}")
            return False
            
        if "availableCars" not in cars_data or not cars_data["availableCars"]:
            print("❌ No cars available for the selected dates and city")
            return False
        
        # Store session data
        self.session.city = city
        self.session.from_date = from_date
        self.session.to_date = to_date
        self.session.available_cars = cars_data["availableCars"]
        
        # Display results
        print(f"\n✅ Found {len(self.session.available_cars)} cars in {city}")
        print(f"📅 From: {from_date} To: {to_date}")
        print(f"⏱️  Duration: {cars_data['duration']}")
        
        return True
    
    async def step2_select_car(self):
        """Step 2: Select a car from available options"""
        print("\n🚗 STEP 2: SELECT A CAR")
        print("-" * 25)
        
        # Display available cars
        for i, car in enumerate(self.session.available_cars, 1):
            print(f"\n{i}. {car['carType']} - {car['carRentalCompanyName']}")
            print(f"   💰 ₹{car['pricePerDay']}/day | Total: ₹{car['totalPrice']} ({car['days']} days)")
        
        print(f"\n0. Go back to search")
        
        while True:
            try:
                choice = self.get_user_input(f"\nSelect a car (1-{len(self.session.available_cars)}): ", "int")
                
                if choice == 0:
                    return "back"
                elif 1 <= choice <= len(self.session.available_cars):
                    self.session.selected_car = self.session.available_cars[choice - 1]
                    
                    print(f"\n✅ Selected: {self.session.selected_car['carType']} - {self.session.selected_car['carRentalCompanyName']}")
                    print(f"💰 Total Price: ₹{self.session.selected_car['totalPrice']}")
                    return True
                else:
                    print(f"❌ Please select a number between 1 and {len(self.session.available_cars)}")
                    
            except ValueError:
                print("❌ Please enter a valid number")
    
    async def step3_confirm_booking(self):
        """Step 3: Confirm the booking"""
        print("\n🎫 STEP 3: CONFIRM BOOKING")
        print("-" * 28)
        
        car = self.session.selected_car
        print("📋 Booking Summary:")
        print(f"   🏙️  City: {self.session.city}")
        print(f"   📅 Dates: {self.session.from_date} to {self.session.to_date}")
        print(f"   🚗 Car: {car['carType']} - {car['carRentalCompanyName']}")
        print(f"   💰 Total Price: ₹{car['totalPrice']} ({car['days']} days)")
        
        confirm = input("\n🤔 Confirm booking? (y/n): ").strip().lower()
        
        if confirm != 'y':
            print("❌ Booking cancelled")
            return False
        
        print("\n⏳ Creating booking...")
        booking_data = await self.client.book_car(
            self.session.city,
            self.session.from_date,
            self.session.to_date,
            car['carType']
        )
        
        if "error" in booking_data or not booking_data.get("success"):
            print(f"❌ Booking failed: {booking_data.get('error', 'Unknown error')}")
            return False
        
        # Store booking details
        self.session.booking_number = booking_data['bookingNumber']
        self.session.total_price = booking_data['totalPrice']
        self.session.booking_confirmed = True
        
        print("\n✅ BOOKING CONFIRMED!")
        print("-" * 25)
        print(f"🎫 Booking Number: #{self.session.booking_number}")
        print(f"💰 Total Amount: ₹{self.session.total_price}")
        print("💳 Payment Status: Pending")
        
        return True
    
    async def step4_make_payment(self):
        """Step 4: Complete payment"""
        print("\n💳 STEP 4: COMPLETE PAYMENT")
        print("-" * 30)
        
        print(f"🎫 Booking Number: #{self.session.booking_number}")
        print(f"💰 Amount to Pay: ₹{self.session.total_price}")
        
        confirm = input(f"\n🤔 Proceed with payment of ₹{self.session.total_price}? (y/n): ").strip().lower()
        
        if confirm != 'y':
            print("❌ Payment cancelled")
            return False
        
        print("\n⏳ Processing payment...")
        payment_data = await self.client.make_payment(self.session.booking_number, self.session.total_price)
        
        if "error" in payment_data or not payment_data.get("success"):
            print(f"❌ Payment failed: {payment_data.get('error', 'Unknown error')}")
            return False
        
        self.session.payment_completed = True
        
        print("\n✅ PAYMENT SUCCESSFUL!")
        print("-" * 25)
        print(f"💳 {payment_data['message']}")
        print(f"🎫 Transaction ID: {payment_data['transactionId']}")
        print(f"📋 Booking Number: #{payment_data['bookingNumber']}")
        
        return True
    
    async def view_booking_status(self, booking_number: Optional[int] = None):
        """View booking status"""
        if booking_number is None:
            booking_number = self.session.booking_number
        
        if booking_number is None:
            booking_number = self.get_user_input("Enter booking number: ", "int")
        
        print("\n⏳ Fetching booking status...")
        status_data = await self.client.get_booking_status(booking_number)
        
        if "error" in status_data:
            print(f"❌ Error: {status_data['error']}")
            return
        
        if not status_data.get("success"):
            print("❌ Failed to get booking status")
            return
        
        booking = status_data["booking"]
        print(f"\n📋 BOOKING STATUS - #{booking['bookingNumber']}")
        print("-" * 50)
        print(f"🏙️  City: {booking['city']}")
        print(f"🚗 Car Type: {booking['carType']}")
        print(f"🏢 Company: {booking['company']}")
        print(f"📅 From: {booking['fromDate']} To: {booking['toDate']}")
        print(f"💰 Price per Day: ₹{booking['pricePerDay']}")
        print(f"📊 Total Days: {booking['totalDays']}")
        print(f"💵 Total Price: ₹{booking['totalPrice']}")
        print(f"📊 Status: {booking['status']}")
        print(f"💳 Payment Status: {booking['paymentStatus']}")
        
        if "transactionId" in booking:
            print(f"🎫 Transaction ID: {booking['transactionId']}")
    
    async def handle_booking_flow(self):
        """Handle the complete booking flow"""
        while True:
            self.print_booking_flow_menu()
            
            try:
                choice = input("Enter your choice: ").strip()
                
                if choice == "0":
                    # Back to main menu
                    return
                
                elif choice == "1":
                    if not self.session.city:
                        # Step 1: Search for cars
                        success = await self.step1_search_cars()
                        if success:
                            print("\n➡️  Proceeding to car selection...")
                            await asyncio.sleep(1)
                    
                    elif not self.session.selected_car:
                        # Step 2: Select a car
                        result = await self.step2_select_car()
                        if result == "back":
                            self.session.city = None
                            self.session.available_cars = []
                        elif result:
                            print("\n➡️  Proceeding to booking confirmation...")
                            await asyncio.sleep(1)
                    
                    elif not self.session.booking_confirmed:
                        # Step 3: Confirm booking
                        success = await self.step3_confirm_booking()
                        if success:
                            print("\n➡️  Proceeding to payment...")
                            await asyncio.sleep(1)
                    
                    elif not self.session.payment_completed:
                        # Step 4: Make payment
                        success = await self.step4_make_payment()
                        if success:
                            print("\n🎉 BOOKING COMPLETE! 🎉")
                            await asyncio.sleep(2)
                    
                    else:
                        # View final status
                        await self.view_booking_status()
                
                elif choice == "2":
                    if not self.session.selected_car:
                        # Search again
                        self.session.reset()
                    elif not self.session.booking_confirmed:
                        # Choose different car
                        self.session.selected_car = None
                    elif not self.session.payment_completed:
                        # View booking details
                        await self.view_booking_status()
                    else:
                        # Start new booking
                        self.session.reset()
                        print("\n🆕 Starting new booking...")
                
                elif choice == "3" and not self.session.booking_confirmed:
                    # Search again
                    self.session.reset()
                
                else:
                    print("❌ Invalid choice. Please try again.")
                    
            except KeyboardInterrupt:
                print("\n\n👋 Returning to main menu...")
                return
            except Exception as e:
                print(f"❌ An error occurred: {e}")

    async def run(self):
        """Run the CLI application"""
        self.print_banner()
        
        # List available tools on startup
        try:
            tools = await self.client.list_available_tools()
            print(f"🔧 Available MCP Tools: {', '.join(tools)}")
        except Exception as e:
            print(f"⚠️  Could not list tools: {e}")
            
        while True:
            self.print_main_menu()
            
            try:
                choice = input("Enter your choice (1-4): ").strip()
                
                if choice == "1":
                    # Start new booking flow
                    self.session.reset()
                    await self.handle_booking_flow()
                
                elif choice == "2":
                    # Check existing booking status
                    print("\n📋 CHECK BOOKING STATUS")
                    await self.view_booking_status()
                
                elif choice == "3":
                    # List available tools
                    print("\n🔧 AVAILABLE MCP TOOLS")
                    try:
                        tools = await self.client.list_available_tools()
                        for i, tool in enumerate(tools, 1):
                            print(f"{i}. {tool}")
                    except Exception as e:
                        print(f"❌ Error listing tools: {e}")
                
                elif choice == "4":
                    # Exit
                    print("\n👋 Thank you for using Car Booking Service!")
                    break
                
                else:
                    print("❌ Invalid choice. Please select 1-4.")
                    
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ An error occurred: {e}")


def check_server_file():
    """Check for server file - updated to avoid conflict with client main.py"""
    server_files = ["main.py"]
    for filename in server_files:
        if os.path.exists(filename):
            return filename
    
    return None

async def main():
    print("🚀 Starting Car Booking MCP Client...")
    
    # Check for server file
    server_file = check_server_file()
    if not server_file:
        print("❌ Server file not found!")
        print("Please make sure one of these files exists in the current directory:")
        print("main.py")  
        print("\nNote: This client file should be named differently from the server file.")
        return
    
    print(f"📁 Found server file: {server_file}")
    
    # Server command
    server_command = [sys.executable, server_file]
    print(f"📋 Server command: {' '.join(server_command)}")
    
    try:
        async with CarBookingMCPClient(server_command) as client:
            print("✅ MCP Client connected successfully!")
            cli = CarBookingCLI(client)
            await cli.run()
            
    except Exception as e:
        print(f"❌ Failed to start client: {e}")
        print("\nTroubleshooting tips:")
        print("1. Make sure Python is in your PATH")
        print("2. Install required dependencies: pip install mcp")
        print("3. Check that the server file has no syntax errors")
        print("4. Try running the server file directly first: python", server_file)
        print("5. Make sure the server file implements proper MCP server protocols")


if __name__ == "__main__":
    # Set event loop policy for Windows
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    # Run the MCP client
    asyncio.run(main())