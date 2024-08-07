from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from pymongo import MongoClient, ASCENDING, DESCENDING
from bson.objectid import ObjectId
import json

app = FastAPI()

client = MongoClient("mongodb://localhost:27017/")  
db = client.course_database
courses_collection = db.courses

class Chapter(BaseModel):
    name: str
    text: str

class Course(BaseModel):
    name: str
    date: int
    description: str
    domain: list
    chapters: list[Chapter]

class CourseResponse(BaseModel):
    id: str
    name: str
    date: int
    description: str
    domain: list
    chapters: list[Chapter]

class Rating(BaseModel):
    rating: bool

def seed_data():
    with open('courses.json', 'r') as file:
        courses = json.load(file)
        for course in courses:
            courses_collection.update_one(
                {"name": course['name']},
                {"$set": course},
                upsert=True
            )
        courses_collection.create_index([("name", ASCENDING)])
        courses_collection.create_index([("date", DESCENDING)])
        print("Database seeded.")

seed_data()

@app.get("/courses", response_model=list[CourseResponse])
async def get_courses(sort_by: str = "alphabetical", domain: str = None):
    sort_options = {
        "alphabetical": ("name", ASCENDING),
        "date": ("date", DESCENDING)
    }

    if sort_by not in sort_options:
        raise HTTPException(status_code=400, detail="Invalid sort option")

    sort_field, sort_order = sort_options[sort_by]
    query = {"domain": {"$in": [domain]}} if domain else {}
    courses = list(courses_collection.find(query).sort(sort_field, sort_order))
    
    for course in courses:
        course['id'] = str(course['_id'])
        del course['_id']

    return courses

@app.get("/courses/{course_id}", response_model=CourseResponse)
async def get_course_overview(course_id: str):
    course = courses_collection.find_one({"_id": ObjectId(course_id)})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    course['id'] = str(course['_id'])
    del course['_id']
    return course

@app.get("/courses/{course_id}/chapters/{chapter_name}", response_model=Chapter)
async def get_chapter_info(course_id: str, chapter_name: str):
    course = courses_collection.find_one({"_id": ObjectId(course_id)})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    chapter = next((ch for ch in course["chapters"] if ch["name"] == chapter_name), None)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    
    return chapter

@app.post("/courses/{course_id}/rate")
async def rate_course(course_id: str, rating: Rating):
    course = courses_collection.find_one({"_id": ObjectId(course_id)})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    update_field = "positive_ratings" if rating.rating else "negative_ratings"
    result = courses_collection.update_one(
        {"_id": ObjectId(course_id)},
        {"$inc": {update_field: 1}}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Course not found")

    return {"detail": "Rating submitted successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
