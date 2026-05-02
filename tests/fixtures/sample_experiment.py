import argparse
import os
import random
import sys
import time

from researchflow.core.utils import report_arguments


def simulate_training_epoch(epoch_num, total_epochs, num_batches, log_interval, learning_rate, sleep_scale):
    sys.stdout.write(f"Epoch {epoch_num}/{total_epochs} | Learning Rate: {learning_rate:.5f}\n")
    sys.stdout.flush()
    for batch_idx in range(1, num_batches + 1):
        time.sleep(random.uniform(0.005, 0.02) * sleep_scale)
        if batch_idx % log_interval == 0 or batch_idx == num_batches:
            current_loss = random.uniform(0.01, 3.0) / (epoch_num + batch_idx / num_batches)
            current_accuracy = max(0.05, random.uniform(0.5, 0.99) - (current_loss / 5.0))
            sys.stdout.write(
                f"  Batch [{batch_idx:>3}/{num_batches}] - "
                f"Loss: {current_loss:.4f}, Accuracy: {current_accuracy:.4f}\n"
            )
            sys.stdout.flush()
    sys.stdout.write(f"Epoch {epoch_num}/{total_epochs} finished.\n\n")
    sys.stdout.flush()


def main():
    parser = argparse.ArgumentParser(description="Small experiment fixture for ResearchFlow alarm tests.")
    parser.add_argument("--learning-rate", type=float, default=0.001)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--model-architecture", type=str, default="ResNet18")
    parser.add_argument("--dataset-name", type=str, default="CIFAR100")
    parser.add_argument("--optimizer-type", type=str, default="AdamW", choices=["SGD", "Adam", "AdamW", "RMSprop"])
    parser.add_argument("--gpu-ids", type=str, default="0")
    parser.add_argument("--use-mixed-precision", action="store_true")
    parser.add_argument("--checkpoint-save-dir", type=str, default="./test_artifacts/experiment_checkpoints")
    parser.add_argument("--log-batch-interval", type=int, default=50)
    parser.add_argument("--num-dataset-workers", type=int, default=4)
    parser.add_argument("--custom-script-exit-code", type=int, default=0)
    parser.add_argument("--simulate-stderr", action="store_true")
    parser.add_argument("--total-runtime-factor", type=float, default=0.0)

    args = parser.parse_args()
    report_arguments(args)

    sys.stdout.write("=== ResearchFlow Sample Experiment Started ===\n")
    sys.stdout.write(f"Model: {args.model_architecture}, Dataset: {args.dataset_name}\n")
    sys.stdout.write(f"Epochs: {args.epochs}, Batch Size: {args.batch_size}, LR: {args.learning_rate}\n")
    sys.stdout.write(f"Using GPUs: [{args.gpu_ids}], Mixed Precision: {args.use_mixed_precision}\n")
    sys.stdout.write(f"Checkpoint Directory: {os.path.abspath(args.checkpoint_save_dir)}\n")
    sys.stdout.flush()

    os.makedirs(args.checkpoint_save_dir, exist_ok=True)
    num_batches_per_epoch = random.randint(80, 120)
    for epoch_num in range(1, args.epochs + 1):
        simulate_training_epoch(
            epoch_num,
            args.epochs,
            num_batches_per_epoch,
            args.log_batch_interval,
            args.learning_rate,
            args.total_runtime_factor,
        )

    if args.simulate_stderr:
        sys.stderr.write("stderr: simulated warning from sample experiment.\n")
        sys.stderr.flush()

    if args.custom_script_exit_code == 0:
        final_model_filename = f"{args.model_architecture}_{args.dataset_name}_epoch{args.epochs}_final.pth"
        final_model_path = os.path.join(args.checkpoint_save_dir, final_model_filename)
        with open(final_model_path, "w", encoding="utf-8") as f:
            f.write(f"Dummy model: {args.model_architecture} on {args.dataset_name}")
        sys.stdout.write(f"Final dummy model saved to: {final_model_path}\n")

    result = "successfully" if args.custom_script_exit_code == 0 else f"with exit code {args.custom_script_exit_code}"
    sys.stdout.write(f"=== ResearchFlow Sample Experiment Finished {result} ===\n")
    sys.stdout.flush()
    sys.exit(args.custom_script_exit_code)


if __name__ == "__main__":
    main()
