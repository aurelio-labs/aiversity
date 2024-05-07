# AIversity: The Adaptive Learning Ecosystem

## Project Description
AIversity is an innovative multi-agent AI tutoring system that aims to revolutionize the way students learn and acquire knowledge. The system adapts to the individual learner's journey, providing a personalized and engaging educational experience. By leveraging advanced AI techniques and a collaborative multi-agent architecture, AIversity creates a dynamic and interactive learning environment that evolves with the student's progress.

Key features of AIversity include:
- Personalized assessment of learning objectives and current knowledge level.
- Dynamic generation of tailored syllabi and curricula
- Adaptive adjustment of content difficulty and depth based on learner's performance
- Continuous refinement of teaching methods and materials
- Emulation of a personal university experience with comprehensive educational support
- Multi-modal content delivery optimized for engagement and knowledge retention

## Architecture
AIversity employs a multi-agent architecture, where specialized agents work together to deliver a seamless and effective learning experience. The system consists of the following key components:

### Triage Agent
The Triage Agent serves as the main interface between the student and the AI tutoring system. It handles user requests, monitors the entire system, and coordinates the activities of other agents. The Triage Agent is responsible for maintaining a consistent and personalized interaction with the student.

### Planning Agent
The Planning Agent oversees the negotiation and planning process among agents for complex tasks. It ensures consistency, facilitates proper information exchange, and monitors the progress and status of assigned tasks. The Planning Agent plays a crucial role in coordinating the collaborative efforts of multiple agents.

### Vision Agent
The Vision Agent is dedicated to processing and analyzing visual documents such as images, PDFs, and scanned materials. It employs OCR techniques to extract text from images and performs further analysis to answer specific questions or provide relevant insights related to the visual content.

### Specialized Agents
AIversity incorporates a wide range of specialized agents, each with specific roles and capabilities, through the ability to spin up generalized agent descriptions. These agents are dynamically spawned based on the requirements of a particular task or project. Examples of specialized agents include:
- Subject Matter Experts
- Question Generators
- Content Creators
- Evaluators and Assessors
- Feedback Providers

## Inter-Agent Communication and Collaboration
Effective communication and collaboration among agents are vital to the success of AIversity. The system employs a messaging service that allows agents to communicate asynchronously, preventing blocking when agents are busy with other tasks. Agents have access to shared workspaces and can dynamically spawn new workspaces as needed for specific projects or subjects.

To ensure seamless coordination and synchronization, AIversity implements the following techniques:
- State-of-Mind: Agents dynamically alter their system prompt context based on the specific interaction or task at hand. This allows for focused and relevant conversations while maintaining a summary of all states of mind.
- Collision Resolution: When an agent is busy and receives a message, a weaker but faster LLM is used to handle the request and determine its urgency. This ensures that the system remains responsive and can prioritize critical tasks.
- Progress Monitoring: The Planning Agent monitors the progress and status of assigned tasks, providing transparency and enabling effective coordination among agents.

## Contributing
As an individual project for an MSc program, AIversity is currently a solo endeavor. However, contributions and collaborations may be considered in the future as the project evolves.

## License
AIversity is released under the MIT License.

## Contact Information
For any inquiries or further information about AIversity, please contact:
- Name: Robert Maye
- Email: robert@aurelio.ai
- GitHub: https://github.com/RobMaye
