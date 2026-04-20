# AI-Agent-Registry
Requirements:
fastapi==0.111.0
uvicorn[standard]==0.29.0
pydantic==1.10.15
 
Q5: How would you extend this to support billing without double-charging?

The current system already has a good base for this because it uses request_id to stop the same usage from being counted twice.

To support billing, I would store each valid usage event as a separate billing record with a status like unbilled or billed.
A billing process would only read records that are still marked unbilled, calculate the amount, and then mark them as billed only after the payment is confirmed.

This way, if the same request is retried or if the system crashes halfway, the same usage will not be charged twice.
So the main idea is: unique request_id + billing status tracking = safe billing without double charging.

Q2: How would you store this data if scale increases to 100K agents?

For a small prototype, in-memory storage is fine, but for 100K agents I would move to a real database like PostgreSQL.

I would store:

agents in an agents table
usage logs in a usage_events table
keep request_id as unique so duplicates are blocked at the database level too

For search, I would use database indexing or full-text search so finding agents stays fast.
For usage summary, I would either precompute totals or store them in a separate summary table so the system does not need to scan all usage records every time.

This would make the system more reliable, scalable, and able to handle multiple server instances.
