import argparse
import json
import sys
import time
import os
import random

from researchflow.core.utils import report_arguments

def simulate_training_epoch(epoch_num, total_epochs, num_batches, log_interval, learning_rate):
    sys.stdout.write(f"Epoch {epoch_num}/{total_epochs} | Learning Rate: {learning_rate:.5f}\n")
    sys.stdout.flush()
    for i in range(1, num_batches + 1):
        time.sleep(random.uniform(0.005, 0.02)) 
        if i % log_interval == 0 or i == num_batches:
            current_loss = random.uniform(0.01, 3.0) / (epoch_num + i/num_batches) 
            current_accuracy = random.uniform(0.5, 0.99) - (current_loss / 5.0)
            if current_accuracy < 0: current_accuracy = 0.05
            sys.stdout.write(f"  Batch [{i:>3}/{num_batches}] - Loss: {current_loss:.4f}, Accuracy: {current_accuracy:.4f}\n")
            sys.stdout.flush()
    sys.stdout.write(f"Epoch {epoch_num}/{total_epochs} finished.\n\n")
    sys.stdout.flush()

def main():
    parser = argparse.ArgumentParser(description="Simulated Deep Learning Experiment Script for ResearchFlow Alarm.")
    
    parser.add_argument('--learning-rate', type=float, default=0.001, help='Initial learning rate.')
    parser.add_argument('--batch-size', type=int, default=64, help='Input batch size for training.')
    parser.add_argument('--epochs', type=int, default=5, help='Number of epochs to train.')
    parser.add_argument('--model-architecture', type=str, default='ResNet18', help='Model architecture name.')
    parser.add_argument('--dataset-name', type=str, default='CIFAR100', help='Name of the dataset.')
    parser.add_argument('--optimizer-type', type=str, default='AdamW', choices=['SGD', 'Adam', 'AdamW', 'RMSprop'], help='Optimizer.')
    parser.add_argument('--gpu-ids', type=str, default='0', help='GPU IDs to use (e.g., "0" or "0,1").')
    parser.add_argument('--use-mixed-precision', action='store_true', help='Enable Automatic Mixed Precision.')
    parser.add_argument('--checkpoint-save-dir', type=str, default='./experiment_checkpoints', help='Directory to save model checkpoints.')
    parser.add_argument('--log-batch-interval', type=int, default=50, help='Log training status every N batches.')
    parser.add_argument('--num-dataset-workers', type=int, default=4, help='Number of worker threads for data loading.')

    parser.add_argument("--custom-script-exit-code", type=int, default=0, help="Custom exit code for the script.")
    parser.add_argument("--enable-arg-printing", action="store_true", help="Print arguments using the researchflow utility.")
    parser.add_argument("--simulate-stderr", action="store_true", help="Generate sample stderr output.")
    parser.add_argument("--total-runtime-factor", type=float, default=0.01, help="Factor to control total runtime by scaling sleeps (e.g. 0.01 for fast, 1.0 for longer).")


    args = parser.parse_args()
    
    # if args.enable_arg_printing:
    report_arguments(args)  

    global_sleep_factor = args.total_runtime_factor

    sys.stdout.write("=== Deep Learning Experiment Simulation Started ===\n")
    sys.stdout.write(f"Model: {args.model_architecture}, Dataset: {args.dataset_name}\n")
    sys.stdout.write(f"Epochs: {args.epochs}, Batch Size: {args.batch_size}, LR: {args.learning_rate}, Optimizer: {args.optimizer_type}\n")
    sys.stdout.write(f"Using GPUs: [{args.gpu_ids}], Mixed Precision: {args.use_mixed_precision}\n")
    sys.stdout.write(f"Checkpoint Directory: {os.path.abspath(args.checkpoint_save_dir)}\n")
    sys.stdout.write(f"Number of Dataloader Workers: {args.num_dataset_workers}\n")
    sys.stdout.flush()

    if not os.path.exists(args.checkpoint_save_dir):
        try:
            os.makedirs(args.checkpoint_save_dir, exist_ok=True)
            sys.stdout.write(f"Created checkpoint directory: {os.path.abspath(args.checkpoint_save_dir)}\n")
        except OSError as e:
            sys.stderr.write(f"Warning: Could not create checkpoint directory {args.checkpoint_save_dir}: {e}\n")
            sys.stderr.flush()
    
    num_batches_per_epoch = random.randint(80, 120)

    for epoch_num in range(1, args.epochs + 1):
        simulate_training_epoch(epoch_num, args.epochs, num_batches_per_epoch, args.log_batch_interval, args.learning_rate)
        time.sleep(random.uniform(0.05, 0.1) * global_sleep_factor) 

    if args.simulate_stderr:
        sys.stderr.write("stderr: This is a simulated error message or warning from the DL script.\n")
        if args.custom_script_exit_code < 0 or args.custom_script_exit_code > 255 :
             args.custom_script_exit_code = 1 
        if args.custom_script_exit_code == 0:
             sys.stderr.write("stderr: Note: Script generated stderr but is set to exit successfully (code 0).\n")
        sys.stderr.flush()

    result_message = "successfully" if args.custom_script_exit_code == 0 else f"with errors (exit code {args.custom_script_exit_code})"
    sys.stdout.write(f"=== Deep Learning Experiment Simulation Finished {result_message} ===\n")
    
    if args.custom_script_exit_code == 0:
        final_model_filename = f"{args.model_architecture}_{args.dataset_name}_epoch{args.epochs}_final.pth"
        final_model_path = os.path.join(args.checkpoint_save_dir, final_model_filename)
        try:
            with open(final_model_path, "w") as f:
                f.write(f"Dummy model: {args.model_architecture} on {args.dataset_name}")
            sys.stdout.write(f"Final dummy model saved to: {final_model_path}\n")
        except IOError as e:
            sys.stderr.write(f"Error: Could not write dummy model file to {final_model_path}: {e}\n")
            sys.stderr.flush()
            if args.custom_script_exit_code == 0 : args.custom_script_exit_code = 77

    sys.stdout.flush()
    sys.exit(args.custom_script_exit_code)

if __name__ == "__main__":
    main()