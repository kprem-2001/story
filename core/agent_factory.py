# core/agent_factory.py
import random

def generate_agent_profile(name, role, traits=None, goal=None, conflict=None):
    """
    Generates a character profile dictionary with name, role, and randomly
    selected traits, goal, and internal conflict if not provided.
    """
    traits_pool = [
        "brave", "cunning", "loyal", "ambitious", "empathetic", "stoic",
        "charming", "rebellious", "curious", "mysterious", "hot-headed", "wise",
        "sarcastic", "calm under pressure", "dreamy", "vengeful", "nurturing"
    ]
    goals_pool = [
        "protect the kingdom", "uncover a hidden truth", "seek revenge", "restore balance",
        "find a lost artifact", "earn redemption", "prove their worth", "break a family curse",
        "reunite with a lost love", "gain ultimate power", "escape a prophecy", "solve a centuries-old mystery"
    ]
    internal_conflicts_pool = [
        "fear of failure", "struggles with identity", "past betrayal", "moral dilemma",
        "unresolved guilt", "conflicting loyalties", "haunted by a dark secret",
        "desperate for approval", "trauma from the past", "resentment toward authority"
    ]

    num_traits_to_sample = min(3, len(traits_pool))

    profile = {
        "name": name,
        "role": role or "character", 
        "traits": traits if traits is not None else random.sample(traits_pool, k=num_traits_to_sample),
        "goal": goal if goal is not None else random.choice(goals_pool),
        "internal_conflict": conflict if conflict is not None else random.choice(internal_conflicts_pool),
    }
    return profile


def describe_agent(agent: dict) -> str:
    """
    Returns a human-readable string describing an agent's profile.
    """
    if not isinstance(agent, dict):
        return "Invalid agent data provided."
        
    trait_list = agent.get('traits', [])
    traits_str = ", ".join(map(str, trait_list)) if trait_list else "not specified"
    
    return (
        f"{agent.get('name', 'Unnamed Agent')} is a {agent.get('role', 'character')} who is {traits_str}. "
        f"Their main goal is to {agent.get('goal', 'achieve something')}. "
        f"They are haunted by {agent.get('internal_conflict', 'an unknown issue')}."
    )