from pydantic import BaseModel, ConfigDict, Field


class Chapter(BaseModel):
    """A Ducks Unlimited chapter."""

    model_config = ConfigDict(frozen=True)

    chapter_id: str  #mandatory 
    chapter_name: str #mandatory 
    city: str | None
    state: str = Field(min_length=2, max_length=2) #mandatory 
    latitude: float | None
    longitude: float | None
