
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from pydantic import BaseModel
from database import async_session, init_db
from models import Book, Review

app = FastAPI()

class BookCreate(BaseModel):
    title: str
    author: str
    content: str

class BookUpdate(BaseModel):
    title: str
    author: str
    content: str

class ReviewCreate(BaseModel):
    rating: float
    comment: str

class BookResponse(BaseModel):
    id: int
    title: str
    author: str
    content: str
    reviews: List[ReviewCreate]

class ReviewResponse(BaseModel):
    id: int
    rating: float
    comment: str
    book_id: int

@app.on_event("startup")
async def on_startup():
    await init_db()


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session

@app.post("/books", response_model=BookResponse)
async def create_book(book: BookCreate, session: AsyncSession = Depends(get_session)):
    new_book = Book(**book.dict())
    session.add(new_book)
    await session.commit()
    await session.refresh(new_book)
    return new_book

@app.get("/books", response_model=List[BookResponse])
async def get_books(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Book).options(selectinload(Book.reviews)))
    books = result.scalars().all()
    return books

@app.get("/books/{id}", response_model=BookResponse)
async def get_book(id: int, session: AsyncSession = Depends(get_session)):
    book = await session.get(Book, id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book

@app.put("/books/{id}", response_model=BookResponse)
async def update_book(id: int, book_update: BookUpdate, session: AsyncSession = Depends(get_session)):
    book = await session.get(Book, id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    for key, value in book_update.dict().items():
        setattr(book, key, value)
    session.add(book)
    await session.commit()
    await session.refresh(book)
    return book

@app.delete("/books/{id}")
async def delete_book(id: int, session: AsyncSession = Depends(get_session)):
    book = await session.get(Book, id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    await session.delete(book)
    await session.commit()
    return {"detail": "Book deleted"}

@app.post("/books/{id}/reviews", response_model=ReviewResponse)
async def create_review(id: int, review: ReviewCreate, session: AsyncSession = Depends(get_session)):
    book = await session.get(Book, id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    new_review = Review(**review.dict(), book_id=id)
    session.add(new_review)
    await session.commit()
    await session.refresh(new_review)
    return new_review

@app.get("/books/{id}/reviews", response_model=List[ReviewResponse])
async def get_reviews(id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Review).filter(Review.book_id == id))
    reviews = result.scalars().all()
    return reviews

@app.get("/books/{id}/summary")
async def get_summary(id: int, session: AsyncSession = Depends(get_session)):
    book = await session.get(Book, id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    result = await session.execute(select(Review).filter(Review.book_id == id))
    reviews = result.scalars().all()
    if not reviews:
        return {"summary": "No reviews yet", "average_rating": None}
    average_rating = sum(review.rating for review in reviews) / len(reviews)
    return {"summary": f"{len(reviews)} reviews", "average_rating": average_rating}

@app.get("/recommendations")
async def get_recommendations(session: AsyncSession = Depends(get_session)):
    
    result = await session.execute(select(Book))
    books = result.scalars().all()
    return books[:5]  

@app.post("/generate-summary")
async def generate_summary(content: str):
    
    summary = content[:100]  
    return {"summary": summary}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
