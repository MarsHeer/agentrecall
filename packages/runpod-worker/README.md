# AgentRecall RunPod Worker

Qwen2.5-7B memory processing for AgentRecall Cloud API.

## Deploy

1. Create RunPod account at https://runpod.io
2. Create Serverless Endpoint:
   - Name: agentrecall-processor
   - GPU: RTX 4090 or A40 (16GB+ VRAM)
   - Idle Timeout: 5s
   - Flash: Yes
   - Disk: 50GB
3. Set env vars in Cloud API:
   RUNPOD_ENDPOINT_ID=your-endpoint-id
   RUNPOD_API_KEY=your-runpod-api-key

## Local Testing

pip install -r requirements.txt
python handler.py --rp_serve_api
