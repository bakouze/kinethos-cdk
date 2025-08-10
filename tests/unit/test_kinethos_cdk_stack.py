import aws_cdk as core
import aws_cdk.assertions as assertions

from kinethos_cdk.kinethos_cdk_stack import KinethosCdkStack

# example tests. To run these tests, uncomment this file along with the example
# resource in kinethos_cdk/kinethos_cdk_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = KinethosCdkStack(app, "kinethos-cdk")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
