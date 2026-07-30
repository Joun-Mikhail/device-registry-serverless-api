# 0002 — AWS SAM over CDK or Terraform

## Context

The infrastructure needs to be code. The realistic options were AWS SAM, AWS CDK,
and Terraform.

## Decision

AWS SAM, with everything in a single `template.yaml`.

## Consequence

SAM's serverless resource types collapse a lot of boilerplate: one
`AWS::Serverless::Function` block produces the function, its role, its log group
wiring and its API Gateway route and permission. The same stack in raw
CloudFormation or Terraform is several times longer for no additional clarity,
and most of that extra length is IAM plumbing that SAM's policy templates express
in two lines.

The template is also declarative end to end, which means it can be read top to
bottom by someone who does not know the tool. A CDK stack is a program: reading
it means running it in your head. For a repository whose main purpose is to be
*read*, that matters more than CDK's expressiveness.

What this gives up: SAM is AWS-only, so none of this transfers if the project
ever needed a second cloud. SAM has no real loops or conditionals, so the five
function blocks are near-identical copies where CDK would have written a `for`
loop — genuine duplication that a reviewer will notice. And `sam local` is a
weaker emulator than the real thing, which is part of why this repository has
`scripts/local_server.py` running the handlers directly against a mocked DynamoDB
instead.

CDK would be the better choice if the function count grew enough that the
copy-paste in `template.yaml` became a maintenance problem.
