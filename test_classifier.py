from app.ai.classifier.efficientnet_classifier import predict_disease

result = predict_disease(
    #"test_images/sample.jpg",
#"test_images/0a205a11-1e64-49f7-93c2-ad59312b4f83___RS_HL 0334.JPG",
#"test_images/0ab1cab4-a0c9-4323-9a64-cdafa4342a9b___GHLB2 Leaf 8918.JPG",
#"test_images/0abc57ec-7f3b-482a-8579-21f3b2fb780b___RS_Erly.B 7609.JPG",
#"test_images/0b2bdc8e-90fd-4bb4-bedb-485502fe8a96___RS_LB 4906.JPG",
"test_images/0f4ebc5a-d646-436a-919d-961342997cde___RS_HL 4183.JPG"
)

print(result)