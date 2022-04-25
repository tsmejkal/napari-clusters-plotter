import sys
import time

import numpy as np
from skimage import measure

sys.path.append("../")


def test_clustering_widget(make_napari_viewer):

    import napari_clusters_plotter as ncp

    viewer = make_napari_viewer()
    widget_list = ncp.napari_experimental_provide_dock_widget()
    n_wdgts = len(viewer.window._dock_widgets)

    for widget in widget_list:
        _widget = widget(viewer)

        if isinstance(
            _widget, ncp._dimensionality_reduction.DimensionalityReductionWidget
        ):
            plot_widget = _widget

    viewer.window.add_dock_widget(plot_widget)
    assert len(viewer.window._dock_widgets) == n_wdgts + 1


def test_bad_measurements(make_napari_viewer):

    from napari_clusters_plotter._dimensionality_reduction import (
        DimensionalityReductionWidget,
    )
    from napari_clusters_plotter._utilities import set_features

    label = np.array(
        [
            [0, 0, 0, 0, 0, 0, 0],
            [0, 1, 1, 0, 0, 2, 2],
            [0, 0, 0, 0, 2, 2, 2],
            [3, 3, 0, 0, 0, 0, 0],
            [0, 0, 4, 4, 0, 0, 0],
            [6, 6, 6, 6, 0, 5, 0],  # <-single pixel label leading to NaN meas.
            [0, 7, 7, 0, 0, 0, 0],
        ]
    )

    viewer = make_napari_viewer()
    labels_layer = viewer.add_labels(label)

    # Add NaNs to data
    measurements = measure.regionprops_table(
        label, properties=(["label", "area", "perimeter"])
    )
    for key in list(measurements.keys())[1:]:
        measurements[key] = measurements[key].astype(float)
        measurements[key][4] = np.nan
    set_features(labels_layer, measurements)

    widget = DimensionalityReductionWidget(napari_viewer=viewer)
    widget.run(
        viewer=viewer,
        labels_layer=labels_layer,
        selected_measurements_list=list(measurements.keys()),
        n_neighbours=2,
        perplexity=5,
        selected_algorithm="UMAP",
        standardize=False,
        n_components=2,
        explained_variance=95.0,
        pca_components=0,
    )


def test_call_to_function(make_napari_viewer):

    viewer = make_napari_viewer()

    label = np.array(
        [
            [0, 0, 0, 0, 0, 0, 0],
            [0, 1, 1, 0, 0, 2, 2],
            [0, 0, 0, 0, 2, 2, 2],
            [3, 3, 0, 0, 0, 0, 0],
            [0, 0, 4, 4, 0, 5, 5],
            [6, 6, 6, 6, 0, 5, 0],
            [0, 7, 7, 0, 0, 0, 0],
        ]
    )

    props = measure.regionprops_table(
        label, properties=(["label", "area", "perimeter"])
    )
    label_layer = viewer.add_labels(label, properties=props)

    from napari_clusters_plotter._dimensionality_reduction import (
        DimensionalityReductionWidget,
    )
    from napari_clusters_plotter._utilities import get_layer_tabular_data

    widget = DimensionalityReductionWidget(napari_viewer=viewer)
    widget.run(
        viewer=viewer,
        labels_layer=label_layer,
        selected_measurements_list=["area", "perimeter"],
        n_neighbours=2,
        perplexity=5,
        selected_algorithm="UMAP",
        standardize=False,
        n_components=2,
        explained_variance=95.0,
        pca_components=0,
    )

    # waiting till the thread worker finished
    blocker = qtbot.waitSignal(widget.worker.finished, timeout=1000000)
    blocker.wait()
    # additional waiting so the return_func_umap gets the returned embedding
    # from the thread, and writes the results into properties/features of the labels layer
    time.sleep(5)
    result = get_layer_tabular_data(label_layer)

    assert "UMAP_0" in result.columns
    assert "UMAP_1" in result.columns

    widget.run(
        viewer=viewer,
        labels_layer=label_layer,
        selected_measurements_list=["area", "perimeter"],
        n_neighbours=2,
        perplexity=5,
        selected_algorithm="t-SNE",
        standardize=False,
        n_components=2,
        explained_variance=95.0,
        pca_components=0,
    )

    blocker = qtbot.waitSignal(widget.worker.finished, timeout=1000000)
    blocker.wait()
    time.sleep(5)

    result = get_layer_tabular_data(label_layer)
    assert "t-SNE_0" in result.columns
    assert "t-SNE_1" in result.columns

    widget.run(
        viewer=viewer,
        labels_layer=label_layer,
        selected_measurements_list=["area", "perimeter"],
        n_neighbours=2,
        perplexity=5,
        selected_algorithm="PCA",
        standardize=False,
        n_components=2,
        explained_variance=95.0,
        pca_components=2,
    )

    blocker = qtbot.waitSignal(widget.worker.finished, timeout=10000000)
    blocker.wait()
    time.sleep(10)

    result = get_layer_tabular_data(label_layer)
    assert "PC_0" in result.columns


def test_umap():

    import pandas as pd

    from napari_clusters_plotter._dimensionality_reduction import umap

    X = np.array([[0, 0, 0], [0, 1, 1], [1, 0, 1], [1, 1, 1]])
    n_comp = 2

    nothing, result = umap(pd.DataFrame(X), n_neigh=2, n_components=n_comp, standardize=False)
    # a tuple is returned, where result[0] is the name of
    # the dimensionality reduction method, and the result[1] is the embedding
    assert result.shape[-1] == n_comp


def test_tsne():

    X = np.array([[0, 0, 0], [0, 1, 1], [1, 0, 1], [1, 1, 1]])
    n_comp = 2

    import pandas as pd

    from napari_clusters_plotter._dimensionality_reduction import tsne

    nothing, result = tsne(pd.DataFrame(X), perplexity=5, n_components=2, standardize=False)
    assert result.shape[-1] == n_comp


def test_pca():

    X = np.array([[0, 0, 0], [0, 1, 1], [1, 0, 1], [1, 1, 1]])
    n_comp = 3

    import pandas as pd

    from napari_clusters_plotter._dimensionality_reduction import pca

    nothing, result = pca(
        pd.DataFrame(X), explained_variance_threshold=95.0, n_components=0
    )
    assert result.shape[-1] == n_comp

    nothing, result = pca(
        pd.DataFrame(X), explained_variance_threshold=95.0, n_components=0
    )
    assert result.shape[-1] == n_comp


if __name__ == "__main__":
    pass

    # test_clustering_widget()
    import napari

    test_bad_measurements(napari.Viewer)
    # test_umap()
