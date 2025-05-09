# Product Requirements Document: AI Real Estate Assistant

## Overview
The AI Real Estate Assistant is a conversational AI application designed to help real estate agencies assist potential buyers and renters in finding their ideal properties. The application uses natural language processing and machine learning to understand user preferences and recommend suitable properties from a database.

## Problem Statement
Real estate agents often spend significant time manually matching clients with properties. This process can be inefficient and may not always consider all available options. Additionally, clients may not always be able to articulate all their preferences at once, requiring multiple interactions.

## Target Audience
- Real estate agencies and agents
- Property buyers and renters
- Property managers and landlords

## User Stories

### As a property buyer/renter
- I want to describe my ideal property in natural language
- I want to specify my preferences for location, budget, property type, and amenities
- I want to receive property recommendations that match my criteria
- I want to refine my search based on additional preferences
- I want to compare properties based on various attributes

### As a real estate agent
- I want to quickly find properties that match client requirements
- I want to provide clients with comprehensive property information
- I want to identify negotiation opportunities based on market data
- I want to streamline the property matching process

## Features and Requirements

### Core Features

#### 1. Conversational Interface
- The assistant should engage users in a natural language conversation
- The system should understand and respond to user queries about properties
- The conversation should be persistent, allowing users to refine their search

#### 2. Property Search and Filtering
- The system should search properties based on:
  - Location (city, neighborhood)
  - Budget range
  - Property type (apartment, house, condo)
  - Number of bedrooms and bathrooms
  - Desired amenities (parking, garden, pool)
  - Proximity to points of interest (schools, public transportation)
  
#### 3. Data Integration
- The system should support multiple data sources:
  - Local CSV files
  - External CSV sources via URLs
  - Potential future API integrations

#### 4. Property Recommendations
- The system should provide personalized property recommendations
- Recommendations should include key property details in a structured format
- The system should explain why properties match user criteria

#### 5. AI Capabilities
- Natural language understanding to extract user preferences
- Reasoning capabilities to match preferences with property attributes
- Learning from user interactions to improve recommendations

### Technical Requirements

#### 1. Backend
- Python-based implementation
- Integration with LLM models via LangChain
- Data processing and management with Pandas

#### 2. Frontend
- Web-based UI using Streamlit
- Responsive design suitable for desktop and mobile
- Intuitive conversation interface

#### 3. Data Management
- Support for various data formats (primarily CSV)
- Data normalization and preprocessing
- Efficient querying of property data

#### 4. Deployment
- Cloud deployment via Streamlit Cloud
- Optional local deployment via Docker or standalone application
- Environment management via Poetry

## Architecture

### Components
1. **User Interface Layer**: Streamlit-based web interface
2. **AI Agent Layer**: LLM-powered conversational agent
3. **Data Processing Layer**: CSV loaders and data formatters
4. **Data Storage Layer**: In-memory database and vector stores

### Data Flow
1. User enters preferences through the conversation interface
2. The system processes the input using the AI agent
3. The AI agent queries the property database based on extracted preferences
4. Results are processed and formatted
5. Recommendations are presented to the user
6. The conversation continues with refinement

## Technical Stack
- **Frontend**: Streamlit
- **Backend**: Python
- **AI/ML**: LangChain, OpenAI GPT models, Llama models
- **Data Processing**: Pandas, FastEmbed
- **Vector Storage**: DocArrayInMemorySearch
- **Deployment**: Streamlit Cloud, Docker
- **Package Management**: Poetry

## Versions and Features

### V1 Implementation
- Used `langchain_experimental.agents.agent_toolkits.pandas.base.create_pandas_dataframe_agent`
- Basic property search functionality
- Single-turn conversations

### V2 Implementation (Current)
- Uses different LLM models (OpenAI GPT, Llama)
- Implements RAG with ConversationalRetrievalChain
- Multi-turn conversations
- Enhanced property search and filtering

### Planned Enhancements
- Integration with additional data sources
- Visual property comparisons
- Geographical mapping of properties
- Sentiment analysis for property descriptions
- Support for international property markets

## Success Metrics
- User engagement (conversation length, return rate)
- Property recommendation accuracy
- Conversion rate (inquiries to viewings)
- User satisfaction ratings
- Response time and system performance

## Timeline
- **Phase 1**: Initial prototype development (Completed)
- **Phase 2**: Integration of multiple data sources and LLM models (In progress)
- **Phase 3**: Enhanced user experience and additional features (Future)
- **Phase 4**: Production deployment and optimization (Future)

## Constraints and Limitations
- Dependent on the quality and structure of property data
- Limited to text-based interactions in the current version
- Requiring OpenAI API key for optimal performance
- Performance dependent on available computational resources

## Appendix
For detailed technical implementation, refer to the project repository documentation.
