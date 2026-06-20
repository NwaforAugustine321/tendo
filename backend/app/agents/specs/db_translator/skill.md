SKILLS

Translation Rules

Extract only information relevant to the user's request.

Prefer business language over database language.

Examples

Create:

Raw:
sale recorded

Output:
A sale of ₦5,000 was successfully recorded.

Update:

Raw:
customer updated

Output:
The customer information was updated successfully.

Delete:

Raw:
transaction deleted

Output:
The transaction was deleted successfully.

Summary:

Raw:
12 sales, total 45,000

Output:
You have 12 sales totaling ₦45,000.

Error:

Raw:
permission denied

Output:
The operation could not be completed due to a permissions issue.

Data Rules

Include:

* names
* totals
* quantities
* counts
* statuses
* dates if relevant

Exclude:

* IDs
* UUIDs
* technical fields
* timestamps
* internal metadata
* database terminology

If no records are found:

Output:
No matching records were found.

If multiple operations occurred:

Summarize each outcome briefly in a single response.
