import lambda = require("@aws-cdk/aws-lambda");
import cdk = require("@aws-cdk/core");
import iam = require("@aws-cdk/aws-iam");
import s3 = require("@aws-cdk/aws-s3");
import { Duration } from "@aws-cdk/core";
import events = require("@aws-cdk/aws-events");
import targets = require("@aws-cdk/aws-events-targets");

export class MediaCaptureDemo extends cdk.Stack {
  constructor(scope: cdk.Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const mediaCaptureBucket = new s3.Bucket(this, "mediaCaptureBucket", {
      publicReadAccess: false,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
    });

    const mediaCaptureBucketPolicy = new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: ["s3:PutObject", "s3:PutObjectAcl"],
      resources: [
        mediaCaptureBucket.bucketArn,
        `${mediaCaptureBucket.bucketArn}/*`,
      ],
      sid: "AWSChimeMediaCaptureBucketPolicy",
    });

    mediaCaptureBucketPolicy.addServicePrincipal("chime.amazonaws.com");
    mediaCaptureBucket.addToResourcePolicy(mediaCaptureBucketPolicy);

    const lambdaChimeRole = new iam.Role(this, "LambdaChimeRole", {
      assumedBy: new iam.ServicePrincipal("lambda.amazonaws.com"),
    });

    lambdaChimeRole.addToPolicy(
      new iam.PolicyStatement({
        resources: ["*"],
        actions: ["chime:*"],
      })
    );

    lambdaChimeRole.addManagedPolicy(
      iam.ManagedPolicy.fromAwsManagedPolicyName(
        "service-role/AWSLambdaBasicExecutionRole"
      )
    );
    
    const processLambda = new lambda.DockerImageFunction(this, "proces", {
      code: lambda.DockerImageCode.fromImageAsset("src/processLambda", {
        cmd: ["app.handler"],
        entrypoint: ["/entry.sh"],
      }),
      environment: {
        MEDIA_CAPTURE_BUCKET: mediaCaptureBucket.bucketName,
      },
      timeout: Duration.minutes(15),
      memorySize: 10240,
    });

    mediaCaptureBucket.grantReadWrite(processLambda);

    const processOutputRule = new events.Rule(this, "processRecordingRule", {
      eventPattern: {
        source: ["aws.chime"],
        detailType: ["Chime Media Pipeline State Change"],
        detail: {
          eventType: ["chime:MediaPipelineDeleted"],
        },
      },
    });

    processOutputRule.addTarget(new targets.LambdaFunction(processLambda));
  }
}