import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.models.entities import Room
from backend.app.schemas.timetable_schemas import RoomCreate, RoomOut

router = APIRouter(prefix="/rooms", tags=["Rooms"])

@router.get("", response_model=List[RoomOut])
def get_rooms(db: Session = Depends(get_db)):
    return db.query(Room).all()

@router.post("", response_model=RoomOut)
def create_room(req: RoomCreate, db: Session = Depends(get_db)):
    r = Room(
        id=f"room-{uuid.uuid4().hex[:8]}",
        name=req.name,
        type=req.type,
        lab_type=req.lab_type,
        capacity=req.capacity,
        building=req.building
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return r

@router.delete("/{room_id}")
def delete_room(room_id: str, db: Session = Depends(get_db)):
    r = db.query(Room).filter(Room.id == room_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Room not found")
    db.delete(r)
    db.commit()
    return {"success": True, "message": f"Room '{r.name}' deleted"}
