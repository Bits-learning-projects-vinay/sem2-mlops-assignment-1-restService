# Use the official AWS Lambda Python base image
FROM public.ecr.aws/lambda/python:3.11

# Copy requirements.txt and install dependencies
# We use --no-cache-dir to keep the image slim
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your function code and model
COPY lambda_function.py ${LAMBDA_TASK_ROOT}
# If your model is in a folder, copy that too
# COPY model.pkl ${LAMBDA_TASK_ROOT}

# Set the CMD to your handler (file_name.function_name)
CMD [ "lambda_function.lambda_handler" ]