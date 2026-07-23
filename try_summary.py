import json
from uuid import uuid4
from hospital_command_center.services.summarization_service import SummarizationService

service = SummarizationService()
result = service.summarize(
    encounter_id=uuid4(),
    symptoms="chest pain, sweating, dizziness since this morning",
    urgency="high",
    triage_rationale="Possible cardiac event, needs urgent evaluation",
    patient_name="Ravi Kumar",
    age=45,
)

data = result if isinstance(result, dict) else result.model_dump(mode="json")
print(json.dumps(data, indent=2))
