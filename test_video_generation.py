import httpx
import asyncio
import json

async def test_video_generation():
    url = "http://localhost:8000/api/generate_video"
    
    # Create a sample request payload
    payload = {
        "job_title": "Chemical Plant Operator",
        "job_description": "Operates and monitors chemical processing equipment in an industrial plant",
        "location": "Chemical manufacturing facility",
        "equipment_used": "Control systems, reactors, pumps, valves, monitoring equipment",
        "industry_sector": "Chemical Manufacturing",
        "video_type": "image"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_video_generation())