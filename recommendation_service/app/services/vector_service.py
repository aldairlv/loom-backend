from typing import List, Optional
import numpy as np

def calculate_user_profile_vector(
    current_vector: Optional[np.ndarray], 
    new_interaction_vector: np.ndarray,
    weight: float = 0.3
) -> np.ndarray:
    """
    Calcula el nuevo vector de perfil de un usuario basado en una nueva interacción.

    Args:
        current_vector: El vector de perfil actual del usuario. Si es None, se usa el de la nueva interacción.
        new_interaction_vector: El vector del post con el que se ha interactuado.
        weight: El peso que se le da a la nueva interacción (0.0 a 1.0). 
                Un valor más alto hace que los intereses cambien más rápido.

    Returns:
        El nuevo vector de perfil del usuario (promedio ponderado).
    """
    if current_vector is None:
        return new_interaction_vector
    
    return (current_vector * (1 - weight)) + (new_interaction_vector * weight)


def calculate_user_profile_vector_batch(
    current_vector: Optional[np.ndarray],
    weighted_vectors: List[np.ndarray],
    weights: List[float]
) -> np.ndarray:
    """
    Calcula el nuevo vector de perfil del usuario combinando el vector actual
    con múltiples vectores de interacción ya ponderados.

    La fórmula usada es: (current_vector + sum(weighted_vectors)) / (1 + sum(weights))
    donde el vector actual tiene peso 1.

    Si `current_vector` es None se devuelve el promedio de los `weighted_vectors`
    normalizado por la suma de pesos.
    """
    if not weighted_vectors or not weights:
        # Nada nuevo: devolver el vector actual o un vector vacío si no existe
        return current_vector if current_vector is not None else np.zeros(512)

    sum_weighted = np.sum(np.stack(weighted_vectors), axis=0)
    total_weight = 1.0 + float(np.sum(np.array(weights)))

    if current_vector is None:
        # Normalizar por la suma de pesos si no existe vector previo
        weight_sum = float(np.sum(np.array(weights)))
        if weight_sum == 0:
            return np.zeros_like(sum_weighted)
        return sum_weighted / weight_sum

    return (current_vector + sum_weighted) / total_weight