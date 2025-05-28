Here are the requiments for claude code to work in the container. 

1. We must use a non root user. lets call it node
2. We must mount .claude.json and .claude from the host home directory into node. 
3. the mount must be read/write
4. the container should have node 18+ installed
5. node package for claude code is npm install -g @anthropic-ai/claude-code
6. Lets just assume a node runtime for now.. ie we will only be working on node projects as well