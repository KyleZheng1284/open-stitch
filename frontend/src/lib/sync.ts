/**
 * Sidebar <-> Canvas sequence sync logic.
 *
 * Both the sidebar list (dnd-kit) and the canvas graph (React Flow)
 * control the same video_sequence. This module provides utilities
 * for keeping them in sync.
 */

/**
 * Compute the new sequence order after a drag-and-drop reorder.
 */
export function reorderSequence<T extends { id: string }>(
  items: T[],
  activeId: string,
  overId: string
): T[] {
  const oldIndex = items.findIndex((item) => item.id === activeId);
  const newIndex = items.findIndex((item) => item.id === overId);

  if (oldIndex === -1 || newIndex === -1) return items;

  const result = [...items];
  const [moved] = result.splice(oldIndex, 1);
  result.splice(newIndex, 0, moved);
  return result;
}

/**
 * Compute React Flow node positions for video sequence.
 * Arranges video nodes in a horizontal chain at the top of the canvas.
 */
export function computeVideoNodePositions(
  videoIds: string[],
  startX: number = 100,
  startY: number = 50,
  spacing: number = 220
): Record<string, { x: number; y: number }> {
  const positions: Record<string, { x: number; y: number }> = {};
  videoIds.forEach((id, idx) => {
    positions[id] = { x: startX + idx * spacing, y: startY };
  });
  return positions;
}
