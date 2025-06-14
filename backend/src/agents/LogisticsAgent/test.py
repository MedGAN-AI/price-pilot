import json
import os
import sys
import time
import unittest
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Tuple
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the parent directory to path to import agent
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from agent import (
        logistics_assistant, 
        initialize_state, 
        handle_carrier_webhook,
        get_agent_status,
        process_batch_requests
    )
    from langchain_core.messages import HumanMessage
except ImportError as e:
    logger.error(f"Error importing agent modules: {e}")
    logger.error("Make sure agent.py and all dependencies are properly installed")
    sys.exit(1)

class LogisticsAgentTester:
    """Enhanced test class for logistics agent"""
    
    def __init__(self, test_data_file: str = "test_data.json"):
        self.test_data_file = test_data_file
        self.test_results = []
        self.start_time = None
        
        # Sample JSON data for testing
        self.SAMPLE_SHIPMENTS = {
            "shipments": [
                {
                    "tracking_number": "AR123456789SA",
                    "carrier": "aramex",
                    "status": "in_transit",
                    "origin": {
                        "city": "Riyadh",
                        "address": "King Fahd Road, Riyadh 12345",
                        "coordinates": {"lat": 24.7136, "lng": 46.6753}
                    },
                    "destination": {
                        "city": "Jeddah",
                        "address": "Corniche Road, Jeddah 21589",
                        "coordinates": {"lat": 21.4858, "lng": 39.1925}
                    },
                    "estimated_delivery": "2025-06-08T14:00:00Z",
                    "current_location": "Riyadh Distribution Center",
                    "service_type": "express",
                    "weight": 2.5,
                    "dimensions": {"length": 30, "width": 20, "height": 15},
                    "last_updated": "2025-06-07T10:30:00Z"
                },
                {
                    "tracking_number": "NQ987654321SA",
                    "carrier": "naqel",
                    "status": "delayed",
                    "origin": {
                        "city": "Dammam",
                        "address": "Industrial Area, Dammam 31441",
                        "coordinates": {"lat": 26.4207, "lng": 50.0888}
                    },
                    "destination": {
                        "city": "Riyadh",
                        "address": "Olaya District, Riyadh 11564",
                        "coordinates": {"lat": 24.6877, "lng": 46.7219}
                    },
                    "estimated_delivery": "2025-06-06T16:00:00Z",  # Past due
                    "current_location": "Dammam Hub - Customs Clearance",
                    "service_type": "standard",
                    "weight": 15.0,
                    "dimensions": {"length": 60, "width": 40, "height": 30},
                    "last_updated": "2025-06-07T08:15:00Z",
                    "delay_reason": "customs_clearance"
                },
                {
                    "tracking_number": "AR555888999SA",
                    "carrier": "aramex",
                    "status": "delivered",
                    "origin": {
                        "city": "Jeddah",
                        "address": "Al-Hamra District, Jeddah 23323",
                        "coordinates": {"lat": 21.5169, "lng": 39.2192}
                    },
                    "destination": {
                        "city": "Mecca",
                        "address": "Aziziyah District, Mecca 24231",
                        "coordinates": {"lat": 21.3891, "lng": 39.8579}
                    },
                    "estimated_delivery": "2025-06-07T12:00:00Z",
                    "actual_delivery": "2025-06-07T11:45:00Z",
                    "current_location": "Delivered - Signed by Ahmed M.",
                    "service_type": "same_day",
                    "weight": 0.5,
                    "dimensions": {"length": 25, "width": 15, "height": 5},
                    "last_updated": "2025-06-07T11:45:00Z"
                },
                {
                    "tracking_number": "INVALID123",  # Invalid tracking number for error testing
                    "carrier": "unknown",
                    "status": "error"
                }
            ],
            "pickup_requests": [
                {
                    "request_id": "PU2025060701",
                    "carrier": "aramex",
                    "pickup_date": "2025-06-08T09:00:00Z",
                    "pickup_location": {
                        "city": "Riyadh",
                        "address": "Business Park, King Abdullah Road",
                        "coordinates": {"lat": 24.7747, "lng": 46.7381}
                    },
                    "destination": {
                        "city": "Dubai",
                        "address": "Dubai International Airport",
                        "coordinates": {"lat": 25.2532, "lng": 55.3657}
                    },
                    "service_type": "international_express",
                    "status": "scheduled",
                    "contact_person": "Sarah Al-Rashid",
                    "contact_phone": "+966501234567"
                }
            ]
        }
    
    def setup(self):
        """Setup test environment"""
        self.start_time = time.time()
        logger.info("🚀 Starting logistics agent test suite")
        
        # Create test data file
        self.save_test_data()
        
        # Verify agent is available
        try:
            status = get_agent_status()
            logger.info(f"🤖 Agent Status: {status['status']}")
            return True
        except Exception as e:
            logger.error(f"❌ Agent not available: {e}")
            return False
    
    def teardown(self):
        """Cleanup after tests"""
        duration = time.time() - self.start_time if self.start_time else 0
        
        # Generate test report
        self.generate_report(duration)
        
        # Cleanup temp files if needed
        # os.remove(self.test_data_file) if you want to clean up
    
    def save_test_data(self):
        """Save sample data to JSON file"""
        with open(self.test_data_file, 'w', encoding='utf-8') as f:
            json.dump(self.SAMPLE_SHIPMENTS, f, indent=2, ensure_ascii=False)
        logger.info(f"✅ Test data saved to {self.test_data_file}")
    
    def load_test_data(self) -> Dict:
        """Load test data from JSON file"""
        try:
            with open(self.test_data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        except Exception as e:
            logger.error(f"❌ Error loading test data: {e}")
            return self.SAMPLE_SHIPMENTS
    
    def record_test_result(self, test_name: str, success: bool, duration: float, 
                          details: str = "", error: str = ""):
        """Record test result for reporting"""
        self.test_results.append({
            "test_name": test_name,
            "success": success,
            "duration": duration,
            "details": details,
            "error": error,
            "timestamp": datetime.now().isoformat()
        })
    
    def measure_response_time(self, func, *args, **kwargs) -> Tuple[Any, float]:
        """Measure function execution time"""
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            success = True
        except Exception as e:
            result = str(e)
            success = False
        duration = time.time() - start_time
        return result, duration, success
    
    def test_single_tracking(self, tracking_number: str, expected_status: str = None) -> bool:
        """Test tracking a single shipment with performance measurement"""
        logger.info(f"🔍 Testing tracking for: {tracking_number}")
        
        def track_shipment():
            state = initialize_state()
            state["messages"] = [HumanMessage(content=f"Track {tracking_number}")]
            response_state = logistics_assistant.invoke(state)
            return response_state["messages"][-1].content
        
        result, duration, success = self.measure_response_time(track_shipment)
        
        if success:
            # Validate response content
            response = result
            status_found = expected_status and expected_status.lower() in response.lower()
            has_tracking_info = any(keyword in response.lower() for keyword in 
                                  ['status', 'location', 'delivery', 'tracking'])
            
            validation_success = status_found or has_tracking_info
            details = f"Response length: {len(response)}, Expected status found: {status_found}"
            
            logger.info(f"✅ Tracking test passed in {duration:.2f}s")
            self.record_test_result(f"track_{tracking_number}", validation_success, 
                                  duration, details)
            return validation_success
        else:
            logger.error(f"❌ Tracking test failed: {result}")
            self.record_test_result(f"track_{tracking_number}", False, duration, 
                                  error=str(result))
            return False
    
    def test_error_handling(self) -> bool:
        """Test agent's error handling capabilities"""
        logger.info("🛡️ Testing error handling...")
        
        error_cases = [
            ("", "Empty query"),
            ("Track ", "Incomplete tracking query"),
            ("Track INVALID123", "Invalid tracking number"),
            ("Schedule pickup without details", "Incomplete pickup request"),
            ("Random gibberish query xyz123", "Nonsensical query")
        ]
        
        results = []
        for query, description in error_cases:
            logger.info(f"Testing: {description}")
            
            def test_error_case():
                state = initialize_state()
                state["messages"] = [HumanMessage(content=query)]
                response_state = logistics_assistant.invoke(state)
                return response_state["messages"][-1].content
            
            result, duration, success = self.measure_response_time(test_error_case)
            
            if success:
                # Check if agent handled error gracefully
                response = result.lower()
                graceful_handling = any(keyword in response for keyword in 
                                      ['sorry', 'unable', 'invalid', 'error', 'help'])
                results.append(graceful_handling)
                
                self.record_test_result(f"error_handling_{description.replace(' ', '_')}", 
                                      graceful_handling, duration)
            else:
                results.append(False)
                self.record_test_result(f"error_handling_{description.replace(' ', '_')}", 
                                      False, duration, error=str(result))
        
        success_rate = sum(results) / len(results) * 100
        logger.info(f"📊 Error handling success rate: {success_rate:.1f}%")
        return success_rate >= 80
    
    def test_performance_benchmarks(self) -> bool:
        """Test response time benchmarks"""
        logger.info("⚡ Testing performance benchmarks...")
        
        test_data = self.load_test_data()
        performance_results = []
        
        # Test different query types with time limits
        benchmark_tests = [
            ("Track AR123456789SA", "single_tracking", 3.0),  # 3 second limit
            ("Schedule pickup from Riyadh", "pickup_scheduling", 5.0),  # 5 second limit
            ("Check Aramex status", "carrier_status", 2.0),  # 2 second limit
        ]
        
        for query, test_type, time_limit in benchmark_tests:
            def run_benchmark():
                state = initialize_state()
                state["messages"] = [HumanMessage(content=query)]
                response_state = logistics_assistant.invoke(state)
                return response_state["messages"][-1].content
            
            result, duration, success = self.measure_response_time(run_benchmark)
            
            within_limit = duration <= time_limit
            performance_results.append(within_limit)
            
            status = "✅" if within_limit else "⚠️"
            logger.info(f"{status} {test_type}: {duration:.2f}s (limit: {time_limit}s)")
            
            self.record_test_result(f"performance_{test_type}", within_limit, duration,
                                  f"Time limit: {time_limit}s")
        
        avg_performance = sum(performance_results) / len(performance_results) * 100
        logger.info(f"📊 Performance benchmark success rate: {avg_performance:.1f}%")
        return avg_performance >= 70
    
    def test_data_validation(self) -> bool:
        """Test data validation and consistency"""
        logger.info("🔍 Testing data validation...")
        
        test_data = self.load_test_data()
        validation_results = []
        
        # Validate shipment data structure
        required_fields = ['tracking_number', 'carrier', 'status', 'origin', 'destination']
        
        for shipment in test_data['shipments']:
            has_required_fields = all(field in shipment for field in required_fields)
            validation_results.append(has_required_fields)
            
            if not has_required_fields:
                missing = [f for f in required_fields if f not in shipment]
                logger.warning(f"⚠️ Missing fields in shipment: {missing}")
        
        # Test with malformed data
        malformed_query = "Track " + json.dumps({"malformed": "data"})
        
        def test_malformed():
            state = initialize_state()
            state["messages"] = [HumanMessage(content=malformed_query)]
            response_state = logistics_assistant.invoke(state)
            return response_state["messages"][-1].content
        
        result, duration, success = self.measure_response_time(test_malformed)
        validation_results.append(success)  # Should handle malformed data gracefully
        
        validation_rate = sum(validation_results) / len(validation_results) * 100
        logger.info(f"📊 Data validation success rate: {validation_rate:.1f}%")
        return validation_rate >= 90
    
    def run_comprehensive_test_suite(self):
        """Run all tests in the comprehensive suite"""
        if not self.setup():
            logger.error("❌ Test setup failed")
            return False
        
        test_data = self.load_test_data()
        
        try:
            # Test 1: Basic tracking functionality
            logger.info("\n" + "="*50)
            logger.info("TEST 1: BASIC TRACKING")
            logger.info("="*50)
            for shipment in test_data['shipments'][:3]:  # Test first 3
                self.test_single_tracking(shipment['tracking_number'], shipment['status'])
            
            # Test 2: Error handling
            logger.info("\n" + "="*50)
            logger.info("TEST 2: ERROR HANDLING")
            logger.info("="*50)
            self.test_error_handling()
            
            # Test 3: Performance benchmarks
            logger.info("\n" + "="*50)
            logger.info("TEST 3: PERFORMANCE BENCHMARKS")
            logger.info("="*50)
            self.test_performance_benchmarks()
            
            # Test 4: Data validation
            logger.info("\n" + "="*50)
            logger.info("TEST 4: DATA VALIDATION")
            logger.info("="*50)
            self.test_data_validation()
            
        except KeyboardInterrupt:
            logger.warning("❌ Tests interrupted by user")
        except Exception as e:
            logger.error(f"❌ Test suite error: {e}")
        finally:
            self.teardown()
    
    def generate_report(self, total_duration: float):
        """Generate comprehensive test report"""
        logger.info("\n" + "="*60)
        logger.info("📊 TEST REPORT")
        logger.info("="*60)
        
        if not self.test_results:
            logger.info("No test results to report")
            return
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r['success'])
        failed_tests = total_tests - passed_tests
        
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        avg_response_time = sum(r['duration'] for r in self.test_results) / total_tests
        
        logger.info(f"📈 Total Tests: {total_tests}")
        logger.info(f"✅ Passed: {passed_tests}")
        logger.info(f"❌ Failed: {failed_tests}")
        logger.info(f"📊 Success Rate: {success_rate:.1f}%")
        logger.info(f"⚡ Average Response Time: {avg_response_time:.2f}s")
        logger.info(f"⏱️ Total Test Duration: {total_duration:.2f}s")
        
        # Show failed tests
        if failed_tests > 0:
            logger.info("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result['success']:
                    logger.info(f"  - {result['test_name']}: {result.get('error', 'Unknown error')}")
        
        # Performance summary
        perf_tests = [r for r in self.test_results if 'performance' in r['test_name']]
        if perf_tests:
            logger.info(f"\n⚡ PERFORMANCE SUMMARY:")
            for test in perf_tests:
                status = "✅" if test['success'] else "⚠️"
                logger.info(f"  {status} {test['test_name']}: {test['duration']:.2f}s")
        
        # Save detailed report to file
        report_file = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump({
                "summary": {
                    "total_tests": total_tests,
                    "passed": passed_tests,
                    "failed": failed_tests,
                    "success_rate": success_rate,
                    "avg_response_time": avg_response_time,
                    "total_duration": total_duration
                },
                "detailed_results": self.test_results
            }, f, indent=2)
        
        logger.info(f"\n📋 Detailed report saved to: {report_file}")


def main():
    """Main test runner"""
    tester = LogisticsAgentTester()
    tester.run_comprehensive_test_suite()


if __name__ == "__main__":
    main()